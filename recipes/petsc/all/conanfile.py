import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, rm, rmdir
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class PetscConan(ConanFile):
    name = "petsc"
    description = (
        "PETSc: the Portable, Extensible Toolkit for Scientific Computation, data "
        "structures and solvers for PDEs (Krylov methods, preconditioners, nonlinear "
        "solvers, time steppers)"
    )
    license = "BSD-2-Clause"
    url = "https://gitlab.com/petsc/petsc"
    homepage = "https://petsc.org"
    topics = ("linear-solvers", "nonlinear-solvers", "pde", "krylov", "hpc", "mpi")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_mpi": [True, False],
        "scalar_type": ["real", "complex"],
        "precision": ["double", "single"],
        "int64": [True, False],
        "with_hypre": [True, False],
        "with_metis": [True, False],
        "with_parmetis": [True, False],
        "with_ptscotch": [True, False],
        "with_superlu_dist": [True, False],
        "with_hdf5": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_mpi": True,
        "scalar_type": "real",
        "precision": "double",
        "int64": False,
        "with_hypre": True,
        "with_metis": True,
        "with_parmetis": True,
        "with_ptscotch": False,
        "with_superlu_dist": True,
        "with_hdf5": False,
        "with_zlib": False,
    }

    # PETSc's own name for the build directory inside the source tree.
    _petsc_arch = "arch-conan"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_mpi:
            # These need MPI; PETSc itself falls back to its MPI stub (MPIUNI).
            for name in ("with_hypre", "with_parmetis", "with_ptscotch", "with_superlu_dist"):
                self.options.rm_safe(name)
        else:
            # Open MPI's static archives define the MPI_* entry points as weak symbols,
            # so a shared library linking libmpi.a does not pull them in and is left
            # with undefined MPI symbols plus a partial copy of the profiling wrappers.
            self.options["openmpi"].shared = True
        # The integer width of every index-carrying dependency has to match PETSc's
        # PetscInt; configure rejects mismatches.
        int64 = bool(self.options.int64)
        if self.options.with_metis or self.options.get_safe("with_parmetis"):
            self.options["metis"].with_64bit_types = int64
        if self.options.get_safe("with_hypre"):
            self.options["hypre"].with_mpi = True
            self.options["hypre"].bigint = int64
        if self.options.get_safe("with_superlu_dist"):
            self.options["superlu_dist"].int64 = int64
            self.options["superlu_dist"].with_parmetis = bool(self.options.get_safe("with_parmetis"))
        if self.options.get_safe("with_ptscotch"):
            self.options["scotch"].with_ptscotch = True
            self.options["scotch"].integer_size = "64" if int64 else "32"
        if self.options.with_hdf5:
            # PETSc never uses HDF5's C++ API. It also accepts a serial HDF5 in an MPI
            # build (it records H5_HAVE_PARALLEL from H5pubconf.h), which is what Conan
            # Center's hdf5 builds: its parallel=True fails to find MPI.
            self.options["hdf5"].enable_cxx = False

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_mpi:
            # petscsys.h includes <mpi.h>; PETSc's API is built on MPI communicators.
            self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        # BLAS and LAPACK; PETSc's C code calls them through its own prototypes.
        self.requires("openblas/[>=0.3.24 <1]")
        if self.options.get_safe("with_hypre"):
            self.requires("hypre/[>=3.2.0 <4]")
        if self.options.with_metis:
            self.requires("metis/[>=5.2.1 <6]")
        if self.options.get_safe("with_parmetis"):
            self.requires("parmetis/[>=4.0.3 <5]")
        if self.options.get_safe("with_ptscotch"):
            self.requires("scotch/[>=7.0.4 <8]")
        if self.options.get_safe("with_superlu_dist"):
            self.requires("superlu_dist/[>=9.2.1 <10]")
        if self.options.with_hdf5:
            # petscviewerhdf5.h includes <hdf5.h>.
            self.requires("hdf5/[>=1.14 <2]", transitive_headers=True)
        if self.options.with_zlib:
            self.requires("zlib/[>=1.2.11 <2]")

    def validate(self):
        if self.settings.os not in ("Linux", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux, FreeBSD and macOS")
        if self.settings.compiler not in ("gcc", "clang", "apple-clang"):
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for gcc and clang")
        if self.options.get_safe("with_parmetis") and not self.options.with_metis:
            raise ConanInvalidConfiguration(f"{self.ref} with with_parmetis=True requires with_metis=True")
        if self.options.get_safe("with_hypre"):
            if self.options.scalar_type == "complex" or self.options.precision != "double":
                raise ConanInvalidConfiguration(
                    f"{self.ref} with with_hypre=True requires scalar_type=real and precision=double: "
                    "the hypre recipe only builds real double precision"
                )
            if bool(self.dependencies["hypre"].options.bigint) != bool(self.options.int64):
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires '-o hypre/*:bigint={self.options.int64}' to match int64"
                )
        if self.options.with_metis or self.options.get_safe("with_parmetis"):
            if bool(self.dependencies["metis"].options.with_64bit_types) != bool(self.options.int64):
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires '-o metis/*:with_64bit_types={self.options.int64}' to match int64"
                )
        if self.options.get_safe("with_superlu_dist"):
            if bool(self.dependencies["superlu_dist"].options.int64) != bool(self.options.int64):
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires '-o superlu_dist/*:int64={self.options.int64}' to match int64"
                )
        if self.options.get_safe("with_ptscotch"):
            scotch = self.dependencies["scotch"].options
            if not scotch.with_ptscotch:
                raise ConanInvalidConfiguration(f"{self.ref} requires '-o scotch/*:with_ptscotch=True'")
            if str(scotch.integer_size) != ("64" if self.options.int64 else "32"):
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires scotch/*:integer_size to match int64 (32 or 64, not default)"
                )
        if self.options.with_hdf5 and self.dependencies["hdf5"].options.parallel and not self.options.with_mpi:
            raise ConanInvalidConfiguration(f"{self.ref} needs with_mpi=True for a parallel hdf5")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @staticmethod
    def _bracket(items):
        # PETSc's configure takes lists as [a,b,c].
        return "[" + ",".join(items) + "]"

    def _closure(self, name):
        # The package and everything it depends on, the package first, so a static
        # library comes before the libraries it needs.
        dep = self.dependencies[name]
        return [dep] + [d for d in dep.dependencies.host.values() if d.package_folder]

    def _include_dirs(self, name):
        dirs = []
        for dep in self._closure(name):
            for d in dep.cpp_info.aggregated_components().includedirs:
                if d not in dirs:
                    dirs.append(d)
        return dirs

    def _lib_flags(self, name):
        # -L/-l flags for a package and all its dependencies. Open MPI's own libraries
        # are left to --with-mpi-lib, and its libompitrace (whose PMPI wrappers print a
        # trace line for every MPI call) must never be linked.
        flags = []
        for dep in self._closure(name):
            if dep.ref.name == "openmpi":
                continue
            info = dep.cpp_info.aggregated_components()
            for d in info.libdirs:
                flag = f"-L{d}"
                if flag not in flags:
                    flags.append(flag)
            for lib in info.libs + info.system_libs:
                # Scotch ships two interchangeable error handlers; scotcherrexit calls
                # exit() on any Scotch error, so PETSc gets the returning ones.
                if lib.endswith("errexit"):
                    continue
                flags.append(f"-l{lib}")
        return flags

    def _package_args(self, option, petsc_name, conan_name):
        if not self.options.get_safe(option):
            return [f"--with-{petsc_name}=0"]
        return [
            f"--with-{petsc_name}=1",
            f"--with-{petsc_name}-include={self._bracket(self._include_dirs(conan_name))}",
            f"--with-{petsc_name}-lib={self._bracket(self._lib_flags(conan_name))}",
        ]

    def _compilers(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        defaults = {"gcc": ("gcc", "g++"), "clang": ("clang", "clang++"), "apple-clang": ("clang", "clang++")}
        cc, cxx = defaults[str(self.settings.compiler)]
        return compilers.get("c", cc), compilers.get("cpp", cxx)

    def _configure_args(self):
        cc, cxx = self._compilers()
        debug = self.settings.build_type == "Debug"
        opt = "-g -O0" if debug else "-O2"
        if self.settings.build_type == "RelWithDebInfo":
            opt = "-g -O2"
        elif self.settings.build_type == "MinSizeRel":
            opt = "-Os"
        if not self.options.shared and self.options.get_safe("fPIC"):
            # configure only knows the PIC flag for shared builds.
            opt += " -fPIC"
        args = [
            f"--prefix={self.package_folder}",
            f"PETSC_ARCH={self._petsc_arch}",
            f"--with-cc={cc}",
            f"--with-cxx={cxx}",
            # Conan's openmpi has no Fortran bindings, and nothing here needs Fortran.
            "--with-fc=0",
            f"--with-debugging={int(debug)}",
            f"COPTFLAGS={opt}",
            f"CXXOPTFLAGS={opt}",
            f"--with-shared-libraries={int(bool(self.options.shared))}",
            f"--with-pic={int(bool(self.options.shared))}",
            f"--with-scalar-type={self.options.scalar_type}",
            f"--with-precision={self.options.precision}",
            f"--with-64-bit-indices={int(bool(self.options.int64))}",
            # Never download anything, and do not pick up optional libraries from the
            # build machine: only what the Conan graph provides.
            "--with-x=0",
            "--with-ssl=0",
            "--with-c2html=0",
            "--with-sowing=0",
            "--with-hwloc=0",
            "--with-yaml=0",
            "--with-openmp=0",
            "--with-cuda=0",
            "--with-hip=0",
            "--with-sycl=0",
            "--with-kokkos=0",
        ]
        if self.options.with_mpi:
            openmpi = self.dependencies["openmpi"]
            info = openmpi.cpp_info.components["ompi"]
            mpi_includes = openmpi.cpp_info.aggregated_components().includedirs
            args += [
                "--with-mpi=1",
                f"--with-mpi-include={self._bracket(mpi_includes)}",
                f"--with-mpi-lib={self._bracket([f'-L{d}' for d in info.libdirs] + ['-lmpi'])}",
                f"--with-mpiexec={os.path.join(openmpi.package_folder, 'bin', 'mpiexec')}",
            ]
        else:
            args.append("--with-mpi=0")

        openblas = self._lib_flags("openblas")
        args.append(f"--with-blaslapack-lib={self._bracket(openblas)}")

        args += self._package_args("with_hypre", "hypre", "hypre")
        args += self._package_args("with_metis", "metis", "metis")
        args += self._package_args("with_parmetis", "parmetis", "parmetis")
        args += self._package_args("with_ptscotch", "ptscotch", "scotch")
        args += self._package_args("with_superlu_dist", "superlu_dist", "superlu_dist")
        args += self._package_args("with_hdf5", "hdf5", "hdf5")
        args += self._package_args("with_zlib", "zlib", "zlib")

        # Conan's metis.h leaves IDXTYPEWIDTH/REALTYPEWIDTH to the compiler command
        # line (its cpp_info.defines), which configure's checks and PETSc's own
        # sources would otherwise not see.
        defines = []
        if self.options.with_metis:
            defines = [d for d in self.dependencies["metis"].cpp_info.aggregated_components().defines
                       if d.startswith(("IDXTYPEWIDTH", "REALTYPEWIDTH"))]
        if defines:
            args.append("CPPFLAGS=" + " ".join(f"-D{d}" for d in defines))
        return args

    def generate(self):
        VirtualBuildEnv(self).generate()
        # configure and the build run small test programs linked to these libraries.
        VirtualRunEnv(self).generate(scope="build")

        # ld resolves the libraries that the shared dependencies need themselves (hwloc
        # for libmpi, say) through LD_LIBRARY_PATH; the -l lists above only name the
        # libraries PETSc links directly.
        env = Environment()
        libdirs = []
        for dep in self.dependencies.host.values():
            if dep.package_folder:
                libdirs += dep.cpp_info.aggregated_components().libdirs
        env.prepend_path("LD_LIBRARY_PATH", libdirs)
        env.vars(self, scope="build").save_script("conan_petsc_libdirs")

    def build(self):
        args = " ".join(f'"{a}"' for a in self._configure_args())
        self.run(f"python3 ./configure {args}", cwd=self.source_folder)
        make = f"make PETSC_DIR={self.source_folder} PETSC_ARCH={self._petsc_arch}"
        self.run(f"{make} MAKE_NP={build_jobs(self)} all", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        self.run(
            f"make PETSC_DIR={self.source_folder} PETSC_ARCH={self._petsc_arch} install",
            cwd=self.source_folder,
        )
        # pkg-config and CMake consumers get the files Conan generates instead.
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # Example/test data, documentation helpers and configure's logs.
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.log", os.path.join(self.package_folder, "lib", "petsc", "conf"))
        rm(self, "reconfigure-*.py", os.path.join(self.package_folder, "lib", "petsc", "conf"))
        rm(self, "uninstall.py", os.path.join(self.package_folder, "lib", "petsc", "conf"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PETSc")
        self.cpp_info.set_property("cmake_target_name", "PETSc::PETSc")
        self.cpp_info.set_property("pkg_config_name", "PETSc")
        self.cpp_info.libs = ["petsc"]

        requires = ["openblas::openblas_component"]
        if self.options.with_mpi:
            # Only the MPI C component: the openmpi package as a whole also carries
            # libompitrace, whose PMPI wrappers print a trace line for every MPI call.
            requires.append("openmpi::ompi-c")
        for option, ref in (
            ("with_hypre", "hypre::hypre"),
            ("with_metis", "metis::metis"),
            ("with_parmetis", "parmetis::parmetis"),
            ("with_superlu_dist", "superlu_dist::superlu_dist"),
            ("with_hdf5", "hdf5::hdf5"),
            ("with_zlib", "zlib::zlib"),
        ):
            if self.options.get_safe(option):
                requires.append(ref)
        if self.options.get_safe("with_ptscotch"):
            requires += ["scotch::libptscotch", "scotch::ptscotcherr"]
        self.cpp_info.requires = requires

        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
        # SuperLU_DIST has C++ parts, and PETSc's C++ sources need the C++ runtime
        # when it is linked statically.
        if not self.options.shared and self.settings.compiler.get_safe("libcxx"):
            libcxx = str(self.settings.compiler.libcxx)
            self.cpp_info.system_libs.append("stdc++" if libcxx.startswith("libstdc++") else "c++")

        # Makefile-based consumers (and SLEPc) find PETSc through PETSC_DIR.
        self.buildenv_info.define_path("PETSC_DIR", self.package_folder)
        self.runenv_info.define_path("PETSC_DIR", self.package_folder)
