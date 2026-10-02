import getpass
import json
import os
import shutil
import textwrap

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs, check_min_cppstd
from conan.tools.env import Environment
from conan.tools.files import copy, get, replace_in_file, save
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class OpenFOAMConan(ConanFile):
    name = "openfoam"
    description = (
        "OpenFOAM by OpenCFD Ltd (openfoam.com): C++ toolbox for computational fluid "
        "dynamics, with its solvers, utilities and libraries"
    )
    license = "GPL-3.0-or-later"
    url = "https://develop.openfoam.com/Development/openfoam"
    homepage = "https://www.openfoam.com"
    topics = ("cfd", "computational-fluid-dynamics", "finite-volume", "hpc", "mpi", "simulation")
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "precision": ["DP", "SP", "SPDP"],
        "label_size": ["32", "64"],
        "with_scotch": [True, False],
        "with_metis": [True, False],
        "with_kahip": [True, False],
        "with_fftw": [True, False],
        "with_cgal": [True, False],
        "with_readline": [True, False],
    }
    default_options = {
        "precision": "DP",
        "label_size": "32",
        "with_scotch": True,
        "with_metis": True,
        "with_kahip": True,
        "with_fftw": True,
        "with_cgal": True,
        "with_readline": True,
    }
    # The build writes into the source tree (wmake builds in place), so every build
    # gets its own copy of the sources.
    no_copy_source = False

    # Captured OpenFOAM environment, relative to the package folder.
    _env_file = os.path.join("conan", "openfoam-environment.json")

    @property
    def _min_cppstd(self):
        # The wmake rules compile with -std=c++17 and the headers need it.
        return 17

    @property
    def _wm_arch(self):
        return {"x86_64": "linux64", "armv8": "linuxARM64"}[str(self.settings.arch)]

    @property
    def _wm_compiler(self):
        return {"gcc": "Gcc", "clang": "Clang"}[str(self.settings.compiler)]

    @property
    def _wm_compile_option(self):
        return "Debug" if self.settings.build_type == "Debug" else "Opt"

    @property
    def _wm_options(self):
        # WM_OPTIONS from etc/config.sh/settings: the platforms/ sub-directory name.
        return (
            f"{self._wm_arch}{self._wm_compiler}{self.options.precision}"
            f"Int{self.options.label_size}{self._wm_compile_option}"
        )

    # With WM_MPLIB=SYSTEMMPI the MPI libraries go into this sub-directory of lib/.
    _foam_mpi = "sys-mpi"

    def configure(self):
        # Open MPI's static archives define the MPI_* entry points as weak symbols,
        # so a shared library linking libmpi.a does not pull them in.
        self.options["openmpi"].shared = True
        # OpenFOAM's Make/options files link these with a bare -l<name> and nothing
        # else, so they have to be shared libraries that carry their own dependencies
        # (static metis would also need GKlib, static kahip OpenMP).
        if self.options.with_scotch:
            self.options["scotch"].shared = True
            self.options["scotch"].with_ptscotch = True
            if self.options.label_size == "64":
                self.options["scotch"].integer_size = "64"
        if self.options.with_metis:
            self.options["metis"].shared = True
            if self.options.label_size == "64":
                self.options["metis"].with_64bit_types = True
        if self.options.with_kahip:
            self.options["kahip"].shared = True
        if self.options.with_fftw:
            self.options["fftw"].shared = True
        if self.options.with_readline:
            self.options["readline"].shared = True
            # The default termcap backend is K&R C that GCC >= 15 (C23) rejects.
            self.options["readline"].with_library = "curses"
        if self.options.with_cgal:
            # CGAL is used header-only; it only needs Boost's headers.
            self.options["boost"].header_only = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Pstream (OpenFOAM's MPI layer) and the parallel decomposition libraries link
        # MPI, and every parallel run needs its mpirun.
        self.requires("openmpi/[>=4.1 <5]", run=True)
        self.requires("zlib/[>=1.2.11 <2]")
        if self.options.with_scotch:
            self.requires("scotch/[>=7.0 <8]")
        if self.options.with_metis:
            self.requires("metis/[>=5.1 <6]")
        if self.options.with_kahip:
            self.requires("kahip/[>=3.15 <4]")
        if self.options.with_fftw:
            self.requires("fftw/[>=3.3 <4]")
        if self.options.with_cgal:
            # Header-only; the libraries that need it link mpfr and gmp directly.
            self.requires("cgal/[>=6.0 <7]")
            self.requires("boost/[>=1.74 <2]")
            self.requires("gmp/[>=6.2 <7]")
            self.requires("mpfr/[>=4.1 <5]")
        if self.options.with_readline:
            self.requires("readline/[>=8.0 <9]")

    def build_requirements(self):
        self.tool_requires("flex/[>=2.6.4 <3]")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} recipe only supports Linux.")
        if str(self.settings.arch) not in ("x86_64", "armv8"):
            raise ConanInvalidConfiguration(f"{self.ref} recipe only supports x86_64 and armv8.")
        if self.settings.compiler not in ("gcc", "clang"):
            raise ConanInvalidConfiguration(
                f"{self.ref} recipe only supports gcc and clang (wmake rules Gcc and Clang)."
            )
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        if self.options.label_size == "64":
            if self.options.with_scotch and self.dependencies["scotch"].options.integer_size != "64":
                raise ConanInvalidConfiguration(
                    f"{self.ref} with label_size=64 requires '-o scotch/*:integer_size=64'"
                )
            if self.options.with_metis and not self.dependencies["metis"].options.with_64bit_types:
                raise ConanInvalidConfiguration(
                    f"{self.ref} with label_size=64 requires '-o metis/*:with_64bit_types=True'"
                )
        if self.options.with_scotch and not self.dependencies["scotch"].options.with_ptscotch:
            raise ConanInvalidConfiguration(
                f"{self.ref} with with_scotch=True requires '-o scotch/*:with_ptscotch=True'"
            )
        if self.options.with_cgal and not self.dependencies["boost"].options.header_only:
            # boost-library rules want libboost_system, which Boost >= 1.69 no longer
            # builds; the header-only flavour is what CGAL needs anyway.
            raise ConanInvalidConfiguration(
                f"{self.ref} with with_cgal=True requires '-o boost/*:header_only=True'"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # Environment variables that point OpenFOAM's configuration at the Conan packages.
    # The same values are used for the build and handed on to consumers, so the
    # installed etc/ files contain no absolute paths into the build machine's cache.
    def _dependency_environment(self):
        env = Environment()

        mpi = self.dependencies["openmpi"]
        mpi_inc = " ".join(f"-isystem {d}" for d in mpi.cpp_info.aggregated_components().includedirs)
        mpi_libdir = mpi.cpp_info.aggregated_components().libdirs[0]
        env.define_path("MPI_ROOT", mpi.package_folder)
        env.define("MPI_ARCH_FLAGS", "-DOMPI_SKIP_MPICXX -DMPICH_SKIP_MPICXX")
        env.define("MPI_ARCH_INC", mpi_inc)
        env.define("MPI_ARCH_LIBS", f"-L{mpi_libdir} -lmpi")

        # etc/config.sh/functions unsets every *_ARCH_PATH when etc/bashrc is sourced,
        # so the locations travel as OPENFOAM_DEP_<NAME> and the config files below
        # copy them over.
        for dep, enabled in self._optional_dependencies:
            if enabled:
                env.define_path(f"OPENFOAM_DEP_{dep.upper()}", self.dependencies[dep].package_folder)
        return env

    @property
    def _optional_dependencies(self):
        return (
            ("scotch", self.options.with_scotch),
            ("metis", self.options.with_metis),
            ("kahip", self.options.with_kahip),
            ("fftw", self.options.with_fftw),
            ("readline", self.options.with_readline),
            ("cgal", self.options.with_cgal),
            ("boost", self.options.with_cgal),
            ("gmp", self.options.with_cgal),
            ("mpfr", self.options.with_cgal),
        )

    # etc/config.sh files that would otherwise point into a ThirdParty tree. Each one
    # now takes the location from the environment (see _dependency_environment) and
    # disables the dependency when it is not set.
    @property
    def _config_files(self):
        def from_env(**names):
            return "".join(
                f'export {var}="${{OPENFOAM_DEP_{dep.upper()}:-none}}"\n' for var, dep in names.items()
            )

        def disabled(*names):
            return "".join(f"export {n}=none\n" for n in names)

        return {
            "scotch": from_env(SCOTCH_ARCH_PATH="scotch"),
            "metis": from_env(METIS_ARCH_PATH="metis"),
            "kahip": from_env(KAHIP_ARCH_PATH="kahip"),
            "FFTW": from_env(FFTW_ARCH_PATH="fftw"),
            "readline": from_env(READLINE_ARCH_PATH="readline"),
            "CGAL": from_env(
                BOOST_ARCH_PATH="boost", CGAL_ARCH_PATH="cgal", GMP_ARCH_PATH="gmp", MPFR_ARCH_PATH="mpfr"
            ),
            # Not packaged for Conan (yet): keep them from finding a stray system copy.
            "adios2": disabled("ADIOS2_ARCH_PATH"),
            "hdf5": disabled("HDF5_ARCH_PATH"),
            "hypre": disabled("HYPRE_ARCH_PATH"),
            "petsc": disabled("PETSC_ARCH_PATH"),
            "umpire": disabled("UMPIRE_ARCH_PATH"),
            "zoltan": disabled("ZOLTAN_ARCH_PATH"),
            "mgridgen": disabled("MGRIDGEN_ARCH_PATH"),
            "ccmio": disabled("CCMIO_ARCH_PATH"),
            "vtk": disabled("VTK_DIR"),
            "paraview": "unset ParaView_DIR ParaView_VERSION\n",
            "gperftools": "",
        }

    def generate(self):
        env = self._dependency_environment()
        # Headers and archives that wmake expects from the system: <zlib.h> and -lz for
        # libOpenFOAM, <FlexLexer.h> for the flex++ scanners. GCC and Clang read both
        # variables, which beats editing every Make/options file.
        zlib = self.dependencies["zlib"].cpp_info.aggregated_components()
        flex = self.dependencies.build["flex"].cpp_info.aggregated_components()
        env.prepend_path("CPATH", zlib.includedirs + flex.includedirs)
        env.prepend_path("LIBRARY_PATH", zlib.libdirs)
        if self.options.with_cgal:
            # The cgal rules look for -lgmp/-lmpfr in <prefix>/lib64 only.
            for dep in ("gmp", "mpfr"):
                env.prepend_path("LIBRARY_PATH", self.dependencies[dep].cpp_info.aggregated_components().libdirs)
        if self.options.with_metis:
            env.define_path("OPENFOAM_DEP_METIS", self._metis_shim())
        if self.options.with_cgal:
            # viewFactorsGen compiles CGAL code that uses GMP numbers (with the gmp and
            # mpfr headers found), but upstream does not link the matching libraries.
            self._patch(
                os.path.join("applications", "utilities", "preProcessing", "viewFactorsGen", "Make", "options"),
                "    -lradiationModels",
                "    -lradiationModels \\\n    $(CGAL_LIBRARIES)",
            )
        if self.options.with_readline:
            # libreadline.so does not record its terminal library (ncurses) as a
            # dependency of its own, so setSet, its only user, links that as well.
            term = []
            for dep in self.dependencies["readline"].dependencies.host.values():
                info = dep.cpp_info.aggregated_components()
                term += [f"-L{d}" for d in info.libdirs] + [f"-l{l}" for l in info.libs + info.system_libs]
            env.define("OPENFOAM_READLINE_LIBS", " ".join(term))
            self._patch(
                os.path.join("applications", "utilities", "mesh", "manipulation", "setSet", "Allwmake"),
                '-lreadline"',
                '-lreadline $OPENFOAM_READLINE_LIBS"',
            )
        env.vars(self, scope="build").save_script("conan_openfoam_deps")

        header = "# Generated by the Conan recipe.\n"
        save(
            self,
            os.path.join(self.source_folder, "etc", "prefs.sh"),
            header
            + textwrap.dedent(f"""\
                export WM_COMPILER={self._wm_compiler}
                export WM_PRECISION_OPTION={self.options.precision}
                export WM_LABEL_SIZE={self.options.label_size}
                export WM_COMPILE_OPTION={self._wm_compile_option}
                # MPI_ROOT, MPI_ARCH_FLAGS, MPI_ARCH_INC and MPI_ARCH_LIBS come from
                # the environment and point at the openmpi package.
                export WM_MPLIB=SYSTEMMPI
                """),
        )
        for name, content in self._config_files.items():
            save(self, os.path.join(self.source_folder, "etc", "config.sh", name), header + content)

    def _patch(self, path, old, new):
        # generate() runs again for 'conan build' and 'conan export-pkg' on the same
        # tree, so a file that is already patched is left alone.
        path = os.path.join(self.source_folder, path)
        with open(path) as f:
            if new in f.read():
                return
        replace_in_file(self, path, old, new)

    def _metis_shim(self):
        # Conan's metis.h leaves IDXTYPEWIDTH and REALTYPEWIDTH to the compiler command
        # line (the package's cpp_info.defines), which OpenFOAM's Make/options do not
        # pass. The build gets a metis prefix of its own instead: a metis.h that defines
        # them and includes the real one, and the real lib directory.
        metis = self.dependencies["metis"].cpp_info.aggregated_components()
        shim = os.path.join(self.generators_folder, "metis")
        content = "#pragma once\n"
        for define in metis.defines:
            name, _, value = define.partition("=")
            content += f"#ifndef {name}\n#define {name} {value or 1}\n#endif\n"
        content += f'#include "{os.path.join(metis.includedirs[0], "metis.h")}"\n'
        save(self, os.path.join(shim, "include", "metis.h"), content)
        lib = os.path.join(shim, "lib")
        if os.path.lexists(lib):
            os.remove(lib)
        os.symlink(metis.libdirs[0], lib)
        return shim

    def _run_bash(self, script, cwd):
        # etc/bashrc needs bash; conan runs commands through /bin/sh. conanrun is
        # needed as well: linking an executable makes ld resolve the DT_NEEDED entries
        # of the shared libraries it links, which it finds through LD_LIBRARY_PATH.
        self.run(f"bash -c '{script}'", cwd=cwd, env=["conanbuild", "conanrun"])

    def build(self):
        self._run_bash(
            f'. etc/bashrc ""; ./Allwmake -j {build_jobs(self)} -s', cwd=self.source_folder
        )
        self._check_build()

    def _check_build(self):
        # Allwmake builds the modules/ with WM_CONTINUE_ON_ERROR, and an application
        # whose optional dependency is not detected is skipped with a warning only, so
        # check for a few representative pieces of each area, including those.
        platform = os.path.join(self.source_folder, "platforms", self._wm_options)
        expected = [
            os.path.join("lib", "libOpenFOAM.so"),
            os.path.join("lib", "libfiniteVolume.so"),
            os.path.join("lib", self._foam_mpi, "libPstream.so"),
            os.path.join("bin", "blockMesh"),
            os.path.join("bin", "checkMesh"),
            os.path.join("bin", "decomposePar"),
            os.path.join("bin", "simpleFoam"),
            os.path.join("bin", "pimpleFoam"),
            os.path.join("bin", "snappyHexMesh"),
        ]
        if self.options.with_scotch:
            expected += [
                os.path.join("lib", "libscotchDecomp.so"),
                os.path.join("lib", self._foam_mpi, "libptscotchDecomp.so"),
            ]
        if self.options.with_metis:
            expected.append(os.path.join("lib", "libmetisDecomp.so"))
        if self.options.with_kahip:
            expected.append(os.path.join("lib", "libkahipDecomp.so"))
        if self.options.with_fftw:
            expected.append(os.path.join("lib", "librandomProcesses.so"))
        if self.options.with_cgal:
            expected.append(os.path.join("bin", "foamyHexMesh"))
        if self.options.with_readline:
            expected.append(os.path.join("bin", "setSet"))
        missing = [f for f in expected if not os.path.exists(os.path.join(platform, f))]
        if missing:
            raise ConanException(
                "OpenFOAM build is incomplete, missing in platforms/"
                f"{self._wm_options}: {', '.join(missing)}. Search the build output for "
                "'Error' to find what failed."
            )

    def package(self):
        src = self.source_folder
        dst = self.package_folder
        copy(self, "LICENSE.md", src=src, dst=os.path.join(dst, "licenses"))

        # The package folder is the OpenFOAM project directory (WM_PROJECT_DIR); its
        # etc/bashrc works out that location by itself.
        for name in ("README.md", "LICENSE.md", "CONTRIBUTORS.md", "CITATION.cff"):
            copy(self, name, src=src, dst=dst)
        # Sources stay in: OpenFOAM's headers include the template definitions (.C)
        # through lnInclude/, and new solvers usually start from an existing one.
        # The tutorials and the build/ object tree are left out.
        for folder in ("META-INFO", "bin", "etc", "wmake", "src", "applications", "platforms"):
            shutil.copytree(
                os.path.join(src, folder),
                os.path.join(dst, folder),
                symlinks=True,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        self._capture_environment()

    def _capture_environment(self):
        # Source the installed etc/bashrc in a clean shell and record what it sets, so
        # package_info can hand the same environment to consumers without them having
        # to source anything.
        dep_vars = dict(self._dependency_environment().vars(self, scope="run").items())
        base = {"HOME": os.path.expanduser("~"), "USER": "conan-openfoam-user", "PATH": "/usr/bin:/bin"}
        exports = " ".join(f"{k}={json.dumps(v)}" for k, v in {**base, **dep_vars}.items())
        out_file = os.path.join(self.build_folder, "openfoam-environment.raw")
        self.run(
            f"env -i {exports} bash -c '. \"$0\"/etc/bashrc \"\" >/dev/null 2>&1; env -0' "
            f'"{self.package_folder}" > "{out_file}"',
            env=[],
        )
        with open(out_file) as f:
            sourced = dict(entry.split("=", 1) for entry in f.read().split("\0") if "=" in entry)

        # Paths into this package, into a dependency or into the user's home become
        # placeholders that package_info resolves on the consuming machine.
        prefixes = [(self.package_folder, "{package_folder}")]
        prefixes += [
            (d.package_folder, f"{{dep:{d.ref.name}}}") for d in self.dependencies.host.values() if d.package_folder
        ]
        prefixes.append((base["HOME"], "{home}"))

        def placeholders(value):
            for prefix, token in prefixes:
                value = value.replace(prefix, token)
            return value.replace(base["USER"], "{user}")

        def prepended(var, original):
            entries = [e for e in sourced.get(var, "").split(":") if e]
            return [placeholders(e) for e in entries if e not in original]

        ignored = set(base) | set(dep_vars) | {"PWD", "OLDPWD", "SHLVL", "_", "MANPATH", "LD_LIBRARY_PATH"}
        captured = {
            "define": {
                k: placeholders(v)
                for k, v in sorted(sourced.items())
                if k not in ignored and not k.startswith("BASH_FUNC_")
            },
            "PATH": prepended("PATH", base["PATH"].split(":")),
            "LD_LIBRARY_PATH": prepended("LD_LIBRARY_PATH", []),
        }
        if "WM_PROJECT_DIR" not in captured["define"]:
            raise ConanException(f"Sourcing etc/bashrc did not set WM_PROJECT_DIR: {sourced}")
        save(self, os.path.join(self.package_folder, self._env_file), json.dumps(captured, indent=2) + "\n")

    def package_info(self):
        # Everything a sourced etc/bashrc would set, for running the OpenFOAM tools and
        # for building against OpenFOAM with wmake.
        with open(os.path.join(self.package_folder, self._env_file)) as f:
            captured = json.load(f)
        tokens = {
            "{package_folder}": self.package_folder,
            "{home}": os.path.expanduser("~"),
            "{user}": getpass.getuser(),
        }
        # Dependencies a consumer does not need (static zlib, say) have no package folder.
        tokens.update(
            {f"{{dep:{d.ref.name}}}": d.package_folder for d in self.dependencies.host.values() if d.package_folder}
        )

        def resolve(value):
            for token, replacement in tokens.items():
                value = value.replace(token, replacement)
            return value

        dep_env = self._dependency_environment()
        for env_info in (self.buildenv_info, self.runenv_info):
            for name, value in captured["define"].items():
                env_info.define(name, resolve(value))
            env_info.prepend_path("PATH", [resolve(p) for p in captured["PATH"]])
            env_info.prepend_path("LD_LIBRARY_PATH", [resolve(p) for p in captured["LD_LIBRARY_PATH"]])
            env_info.compose_env(dep_env)
        # Linking an executable makes ld resolve the DT_NEEDED entries of the libraries
        # it links (libPstream needs libmpi) through LD_LIBRARY_PATH. Conan puts the
        # shared dependencies' lib dirs only into the run environment; wmake builds
        # against this package need them in the build environment too.
        shared_libdirs = []
        for dep in self.dependencies.host.values():
            if dep.package_folder and dep.options.get_safe("shared"):
                shared_libdirs += dep.cpp_info.aggregated_components().libdirs
        self.buildenv_info.append_path("LD_LIBRARY_PATH", shared_libdirs)

        # For CMake and other build systems: the core libraries, header dirs and defines
        # a wmake build would use. Further OpenFOAM libraries can be added to a target by
        # name, they all live in the same lib directory.
        libdir = os.path.join("platforms", self._wm_options, "lib")
        defines = [
            f"OPENFOAM={self.version}",
            f"WM_{self.options.precision}",
            f"WM_LABEL_SIZE={self.options.label_size}",
            "NoRepository",
        ]
        if self.settings.build_type == "Debug":
            defines.append("FULLDEBUG")

        self.cpp_info.set_property("cmake_file_name", "OpenFOAM")
        self.cpp_info.set_property("cmake_target_name", "OpenFOAM::OpenFOAM")

        def component(name, requires=(), includes=None):
            comp = self.cpp_info.components[name]
            comp.set_property("cmake_target_name", f"OpenFOAM::{name}")
            comp.libs = [name]
            comp.libdirs = [libdir]
            comp.includedirs = [os.path.join("src", d, "lnInclude") for d in (includes or [name])]
            comp.defines = defines
            comp.requires = list(requires)
            comp.bindirs = []
            return comp

        core = component("OpenFOAM", includes=["OpenFOAM", os.path.join("OSspecific", "POSIX")])
        # Code that uses Pstream itself (any parallel reduction) links it directly. The MPI
        # libPstream is the one to link; at run time LD_LIBRARY_PATH (see above) also
        # finds it before the serial one in lib/dummy.
        core.libs = ["OpenFOAM", "Pstream"]
        core.libdirs = [libdir, os.path.join(libdir, self._foam_mpi)]
        core.system_libs = ["m", "dl", "pthread"]
        core.requires = ["openmpi::ompi-c", "zlib::zlib"]
        component("fileFormats", ["OpenFOAM"])
        component("surfMesh", ["fileFormats"])
        component("meshTools", ["surfMesh"])
        component("finiteVolume", ["meshTools"])

        # Dependencies that only OpenFOAM's own (plugin) libraries link.
        self.cpp_info.components["_private"].requires = [
            f"{dep}::{dep}" for dep, enabled in self._optional_dependencies if enabled
        ]
        self.cpp_info.components["_private"].includedirs = []
        self.cpp_info.components["_private"].libdirs = []
        self.cpp_info.components["_private"].bindirs = []
