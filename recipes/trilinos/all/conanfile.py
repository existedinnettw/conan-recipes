import glob
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, rm, rmdir, save

required_conan_version = ">=2.0"


class TrilinosConan(ConanFile):
    name = "trilinos"
    description = (
        "Trilinos: object-oriented libraries for large-scale, complex multi-physics "
        "engineering and scientific problems (packaged: Teuchos and the Epetra solver "
        "stack used by deal.II)"
    )
    # BSD-3-Clause for Trilinos itself; TrilinosSS (KLU/AMD/COLAMD, used by Amesos) is
    # LGPL-2.1.
    license = ("BSD-3-Clause", "LGPL-2.1-or-later")
    url = "https://github.com/trilinos/Trilinos"
    homepage = "https://trilinos.github.io"
    topics = ("linear-algebra", "sparse", "solvers", "preconditioners", "hpc", "mpi", "epetra")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_mpi": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_mpi": True,
    }

    # Trilinos packages built, dependencies first, each with its libraries in link
    # order (a library may use the ones after it). Trilinos 17 removed the Epetra
    # stack, so 16.x is the last series with it.
    _packages = {
        "Teuchos": ["teuchosremainder", "teuchosnumerics", "teuchoscomm",
                    "teuchosparameterlist", "teuchosparser", "teuchoscore"],
        "Epetra": ["epetra"],
        "EpetraExt": ["epetraext"],
        "TrilinosSS": ["trilinosss"],
        "AztecOO": ["aztecoo"],
        "Amesos": ["amesos"],
        "Ifpack": ["ifpack"],
        "ML": ["ml"],
    }
    _package_requires = {
        "Teuchos": [],
        "Epetra": ["Teuchos"],
        "EpetraExt": ["Teuchos", "Epetra"],
        "TrilinosSS": [],
        "AztecOO": ["Teuchos", "Epetra"],
        "Amesos": ["Teuchos", "Epetra", "EpetraExt", "TrilinosSS"],
        "Ifpack": ["Teuchos", "Epetra", "EpetraExt", "AztecOO", "Amesos"],
        "ML": ["Teuchos", "Epetra", "EpetraExt", "AztecOO", "Amesos", "Ifpack"],
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.with_mpi:
            # Open MPI's static archives define the MPI_* entry points as weak symbols,
            # which a shared library linking libmpi.a does not pull in.
            self.options["openmpi"].shared = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_mpi:
            # Teuchos and Epetra headers include <mpi.h> and take MPI communicators.
            self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        self.requires("openblas/[>=0.3.24 <1]")

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.os not in ("Linux", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux, FreeBSD and macOS")
        if not self.dependencies["openblas"].options.build_lapack:
            raise ConanInvalidConfiguration(f"{self.ref} requires '-o openblas/*:build_lapack=True'")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @staticmethod
    def _library_files(dep, names):
        # Full paths of the named libraries of a dependency, whichever kind it built.
        info = dep.cpp_info.aggregated_components()
        files = []
        for name in names:
            for libdir in info.libdirs:
                found = sorted(glob.glob(os.path.join(libdir, f"lib{name}.so"))
                               + glob.glob(os.path.join(libdir, f"lib{name}.dylib"))
                               + glob.glob(os.path.join(libdir, f"lib{name}.a")))
                if found:
                    files.append(found[0].replace("\\", "/"))
                    break
        return files

    def generate(self):
        VirtualBuildEnv(self).generate()

        tc = CMakeToolchain(self)
        cppstd = tc.blocks["cppstd"].values.get("cppstd")
        if cppstd and int(cppstd) > 20:
            # TriBITS accepts only C++11, 14, 17 and 20; the library's interface is the
            # same under later standards.
            tc.blocks["cppstd"].values["cppstd"] = "20"
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
        # Only the packages listed above, nothing that TriBITS would enable on its own.
        tc.cache_variables["Trilinos_ENABLE_ALL_PACKAGES"] = False
        tc.cache_variables["Trilinos_ENABLE_ALL_OPTIONAL_PACKAGES"] = False
        # EpetraExt, AztecOO, Amesos, Ifpack and ML are "secondary tested".
        tc.cache_variables["Trilinos_ENABLE_SECONDARY_TESTED_CODE"] = True
        for package in self._packages:
            tc.cache_variables[f"Trilinos_ENABLE_{package}"] = True
        # Optional dependencies of the packages above that are not packaged here.
        for package in ("Kokkos", "Triutils", "Galeri", "Zoltan", "Isorropia"):
            tc.cache_variables[f"Trilinos_ENABLE_{package}"] = False
        tc.cache_variables["Trilinos_ENABLE_TESTS"] = False
        tc.cache_variables["Trilinos_ENABLE_EXAMPLES"] = False
        # Fortran is only needed for Trilinos' own Fortran interfaces; the BLAS/LAPACK
        # name mangling then defaults to lower case with a trailing underscore, which
        # is OpenBLAS'.
        tc.cache_variables["Trilinos_ENABLE_Fortran"] = False
        tc.cache_variables["Trilinos_SHOW_DEPRECATED_WARNINGS"] = False
        if self.settings.compiler in ("gcc", "clang", "apple-clang"):
            # Without Fortran, AztecOO calls its C versions of the Fortran routines
            # without a prototype, which GCC 14 and Clang 16 reject by default.
            tc.extra_cflags.append("-Wno-error=implicit-function-declaration")
        # Makefile.export.* for non-CMake users hard-code the build machine's paths.
        tc.cache_variables["Trilinos_ENABLE_EXPORT_MAKEFILES"] = False
        tc.cache_variables["Trilinos_ASSERT_DEFINED_DEPENDENCIES"] = "OFF"
        # Every optional TPL off, except the ones handed over below.
        tc.cache_variables["Trilinos_ENABLE_ALL_OPTIONAL_TPLS"] = False
        for tpl in ("DLlib", "Pthread", "Boost", "BinUtils", "Netcdf", "HDF5", "METIS",
                    "ParMETIS", "SuperLU", "SuperLUDist", "UMFPACK", "AMD", "HYPRE",
                    "PETSC", "MUMPS", "SCALAPACK", "BLACS", "y12m", "CSparse", "Matio",
                    "yaml-cpp", "X11", "QT", "Valgrind"):
            tc.cache_variables[f"TPL_ENABLE_{tpl}"] = False

        openblas = self.dependencies["openblas"]
        blas_libs = (self._library_files(openblas, ["openblas"])
                     + openblas.cpp_info.aggregated_components().system_libs)
        tc.cache_variables["TPL_ENABLE_BLAS"] = True
        tc.cache_variables["TPL_ENABLE_LAPACK"] = True
        tc.cache_variables["TPL_BLAS_LIBRARIES"] = ";".join(blas_libs)
        tc.cache_variables["TPL_LAPACK_LIBRARIES"] = ";".join(blas_libs)

        tc.cache_variables["TPL_ENABLE_MPI"] = bool(self.options.with_mpi)
        if self.options.with_mpi:
            # TriBITS would replace the compilers with the mpicc/mpicxx it finds on PATH
            # (possibly a system MPI); hand it the openmpi package instead.
            openmpi = self.dependencies["openmpi"]
            mpi = openmpi.cpp_info.components["ompi-c"]
            tc.cache_variables["MPI_USE_COMPILER_WRAPPERS"] = False
            tc.cache_variables["MPI_BASE_DIR"] = openmpi.package_folder.replace("\\", "/")
            tc.cache_variables["TPL_MPI_INCLUDE_DIRS"] = ";".join(
                d.replace("\\", "/") for d in openmpi.cpp_info.aggregated_components().includedirs
            )
            tc.cache_variables["TPL_MPI_LIBRARIES"] = ";".join(self._library_files(openmpi, mpi.libs))
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _cmake_module(self):
        return os.path.join("lib", "cmake", "conan-trilinos-variables.cmake")

    def _write_cmake_module(self):
        # Upstream's TrilinosConfig.cmake (removed: it hard-codes the build machine's
        # BLAS/LAPACK/MPI paths) also defines these lists, which consumers such as
        # deal.II read to learn what the installation contains.
        packages = ";".join(reversed(list(self._packages)))
        tpls = ";".join(["LAPACK", "BLAS"] + (["MPI"] if self.options.with_mpi else []))
        content = textwrap.dedent(f"""\
            set(Trilinos_PACKAGE_LIST "{packages}")
            set(Trilinos_SELECTED_PACKAGE_LIST "{packages}")
            set(Trilinos_TPL_LIST "{tpls}")
            set(Trilinos_SELECTED_TPL_LIST "{tpls}")
            """)
        save(self, os.path.join(self.package_folder, self._cmake_module), content)

    def package(self):
        licenses = os.path.join(self.package_folder, "licenses")
        for pattern in ("LICENSE", "Copyright.txt", "COPYRIGHT"):
            copy(self, pattern, src=self.source_folder, dst=licenses)
        for package in ("teuchos", "epetra", "epetraext", "aztecoo", "ifpack", "ml"):
            for pattern in ("LICENSE", "Copyright.txt", "COPYRIGHT"):
                copy(self, pattern, src=os.path.join(self.source_folder, "packages", package),
                     dst=os.path.join(licenses, package))
        copy(self, "lesser.txt",
             src=os.path.join(self.source_folder, "packages", "common", "auxiliarySoftware",
                              "SuiteSparse", "src", "Doc"),
             dst=os.path.join(licenses, "trilinosss"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # TriBITS' configs for the TPLs (BLAS, LAPACK, MPI), with the build machine's paths.
        rmdir(self, os.path.join(self.package_folder, "lib", "external_packages"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "Makefile.export.*", os.path.join(self.package_folder, "include"))
        self._write_cmake_module()

    def package_info(self):
        # Upstream's CMake names: one <Package>::all_libs target per Trilinos package
        # and Trilinos::all_libs for all of them.
        self.cpp_info.set_property("cmake_file_name", "Trilinos")
        self.cpp_info.set_property("cmake_target_name", "Trilinos::all_libs")
        self.cpp_info.set_property("cmake_build_modules", [self._cmake_module])

        external = ["openblas::openblas_component"]
        if self.options.with_mpi:
            # Only the MPI C component: the openmpi package as a whole also carries
            # libompitrace, whose PMPI wrappers print a trace line for every MPI call.
            external.append("openmpi::ompi-c")
        for package, libs in self._packages.items():
            component = self.cpp_info.components[package.lower()]
            component.set_property("cmake_target_name", f"{package}::all_libs")
            component.libs = libs
            component.requires = [p.lower() for p in self._package_requires[package]] + external
            if self.settings.os in ("Linux", "FreeBSD"):
                component.system_libs = ["m"]
