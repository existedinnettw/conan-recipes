import glob
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, rm, rmdir, save

required_conan_version = ">=2.0"


class DealiiConan(ConanFile):
    name = "dealii"
    description = (
        "deal.II: a C++ finite element library for adaptive, parallel solution of "
        "partial differential equations"
    )
    license = ("Apache-2.0 WITH LLVM-exception", "LGPL-2.1-or-later")
    url = "https://github.com/dealii/dealii"
    homepage = "https://www.dealii.org"
    topics = ("finite-elements", "fem", "pde", "adaptive-mesh-refinement", "hpc", "mpi")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_mpi": [True, False],
        "with_p4est": [True, False],
        "with_petsc": [True, False],
        "with_metis": [True, False],
        "with_lapack": [True, False],
        "with_zlib": [True, False],
        # Explicit instantiations for std::complex number types as well.
        "with_complex_values": [True, False],
        # 64-bit global DoF indices; PETSc then needs 64-bit indices too.
        "int64": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_mpi": True,
        "with_p4est": True,
        "with_petsc": True,
        "with_metis": True,
        "with_lapack": True,
        "with_zlib": True,
        "with_complex_values": False,
        "int64": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_mpi:
            # Both need MPI in deal.II.
            self.options.rm_safe("with_p4est")
            self.options.rm_safe("with_petsc")
        else:
            # Open MPI's static archives define the MPI_* entry points as weak symbols,
            # so a shared library linking libmpi.a does not pull them in and is left
            # with undefined MPI symbols plus a partial copy of the profiling wrappers.
            self.options["openmpi"].shared = True
        if self.options.get_safe("with_p4est"):
            self.options["p4est"].with_mpi = True
            self.options["p4est"].with_p8est = True
        if self.options.get_safe("with_petsc"):
            self.options["petsc"].with_mpi = True
            self.options["petsc"].int64 = bool(self.options.int64)
            if self.options.with_complex_values:
                self.options["petsc"].scalar_type = "complex"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_mpi:
            # deal.II's headers include <mpi.h> and its API takes MPI communicators.
            self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        if self.options.get_safe("with_p4est"):
            # deal.II/distributed/p4est_wrappers.h includes the p4est headers.
            self.requires("p4est/[>=2.8 <3]", transitive_headers=True, transitive_libs=True)
        if self.options.get_safe("with_petsc"):
            # deal.II/lac/petsc_*.h include the PETSc headers.
            self.requires("petsc/[>=3.26 <4]", transitive_headers=True, transitive_libs=True)
        if self.options.with_metis:
            self.requires("metis/[>=5.2.1 <6]")
        if self.options.with_lapack:
            self.requires("openblas/[>=0.3.24 <1]")
        if self.options.with_zlib:
            self.requires("zlib/[>=1.2.11 <2]")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)
        if self.settings.os not in ("Linux", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux, FreeBSD and macOS")
        if self.options.with_lapack and not self.dependencies["openblas"].options.build_lapack:
            raise ConanInvalidConfiguration(
                f"{self.ref} with with_lapack=True requires '-o openblas/*:build_lapack=True'"
            )
        if self.options.get_safe("with_petsc"):
            petsc = self.dependencies["petsc"].options
            if bool(petsc.int64) != bool(self.options.int64):
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires '-o petsc/*:int64={self.options.int64}' to match int64"
                )
            if petsc.scalar_type == "complex" and not self.options.with_complex_values:
                raise ConanInvalidConfiguration(
                    f"{self.ref} with a complex PETSc requires with_complex_values=True"
                )

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
        # configure runs small test programs linked to the dependencies.
        VirtualRunEnv(self).generate(scope="build")

        env = Environment()
        if self.options.with_mpi:
            # CMake's FindMPI interrogates the compiler wrappers, which need the OPAL_*
            # variables of the openmpi package to find their data.
            env.compose_env(self.dependencies["openmpi"].runenv_info)
        env.vars(self, scope="build").save_script("conan_dealii_mpi")

        tc = CMakeToolchain(self)
        # deal.II accepts only these three build types.
        tc.cache_variables["CMAKE_BUILD_TYPE"] = "Debug" if self.settings.build_type == "Debug" else "Release"
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Upstream adds the build machine's dependency paths as RPATH on install.
        tc.cache_variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
        # deal.II enables Fortran when the machine has a compiler for it (only to
        # detect BLAS name mangling). FindMPI then also wants MPI's Fortran bindings,
        # which Conan's openmpi does not build. Skip the probe; OpenBLAS uses the
        # default mangling.
        tc.cache_variables["Fortran_CHECKED"] = True
        tc.cache_variables["DEAL_II_Fortran_COMPILER_WORKS"] = False
        # Otherwise deal.II compiles with -march=native.
        tc.cache_variables["DEAL_II_ALLOW_PLATFORM_INTROSPECTION"] = False
        tc.cache_variables["DEAL_II_COMPONENT_EXAMPLES"] = False
        tc.cache_variables["DEAL_II_COMPONENT_DOCUMENTATION"] = False
        tc.cache_variables["DEAL_II_COMPONENT_PACKAGE"] = False
        tc.cache_variables["DEAL_II_COMPONENT_PYTHON_BINDINGS"] = False
        tc.cache_variables["DEAL_II_WITH_CXX20_MODULE"] = False
        tc.cache_variables["DEAL_II_WITH_64BIT_INDICES"] = bool(self.options.int64)
        tc.cache_variables["DEAL_II_WITH_COMPLEX_VALUES"] = bool(self.options.with_complex_values)

        # Only the features asked for here: no search for optional libraries on the
        # build machine.
        tc.cache_variables["DEAL_II_ALLOW_AUTODETECTION"] = False
        features = {
            "MPI": self.options.with_mpi,
            "P4EST": self.options.get_safe("with_p4est"),
            "PETSC": self.options.get_safe("with_petsc"),
            "METIS": self.options.with_metis,
            "LAPACK": self.options.with_lapack,
            "ZLIB": self.options.with_zlib,
        }
        for feature, enabled in features.items():
            tc.cache_variables[f"DEAL_II_WITH_{feature}"] = bool(enabled)
        for feature in ("ADOLC", "ARBORX", "ARPACK", "ASSIMP", "CGAL", "GINKGO", "GMSH",
                        "GSL", "HDF5", "MUMPS", "NETCDF", "OPENCASCADE", "PSBLAS",
                        "SCALAPACK", "SLEPC", "SUNDIALS", "SYMENGINE", "TBB", "TRILINOS",
                        "VTK"):
            tc.cache_variables[f"DEAL_II_WITH_{feature}"] = False
        # deal.II's own copies, compiled into libdeal_II, rather than whatever the build
        # machine has installed.
        for bundled in ("BOOST", "KOKKOS", "TASKFLOW", "MUPARSER", "UMFPACK", "MAGIC_ENUM"):
            tc.cache_variables[f"DEAL_II_WITH_{bundled}"] = True
            tc.cache_variables[f"DEAL_II_FORCE_BUNDLED_{bundled}"] = True

        if self.options.with_mpi:
            bindir = os.path.join(self.dependencies["openmpi"].package_folder, "bin")
            tc.cache_variables["MPI_C_COMPILER"] = os.path.join(bindir, "mpicc").replace("\\", "/")
            tc.cache_variables["MPI_CXX_COMPILER"] = os.path.join(bindir, "mpicxx").replace("\\", "/")
            tc.cache_variables["MPIEXEC_EXECUTABLE"] = os.path.join(bindir, "mpiexec").replace("\\", "/")
        if self.options.get_safe("with_p4est"):
            p4est = self.dependencies["p4est"].package_folder.replace("\\", "/")
            tc.cache_variables["P4EST_DIR"] = p4est
            tc.cache_variables["SC_DIR"] = p4est
        if self.options.get_safe("with_petsc"):
            tc.cache_variables["PETSC_DIR"] = self.dependencies["petsc"].package_folder.replace("\\", "/")
            tc.cache_variables["PETSC_ARCH"] = ""
        if self.options.with_metis:
            metis = self.dependencies["metis"]
            # deal.II links only libmetis; a static one also needs GKlib.
            tc.cache_variables["METIS_LIBRARY"] = ";".join(
                self._library_files(metis, ["metis"]) + self._library_files(self.dependencies["gklib"], ["GKlib"])
            )
            tc.cache_variables["METIS_DIR"] = metis.package_folder.replace("\\", "/")
            # Conan's metis.h leaves IDXTYPEWIDTH/REALTYPEWIDTH to the compiler command
            # line.
            for define in metis.cpp_info.aggregated_components().defines:
                if define.startswith(("IDXTYPEWIDTH", "REALTYPEWIDTH")):
                    key, value = define.split("=", 1)
                    tc.preprocessor_definitions[key] = value
        if self.options.with_lapack:
            # Handing FindBLAS/FindLAPACK the libraries skips their search, whose link
            # test misses the libm a static OpenBLAS needs unless a Fortran compiler
            # is enabled.
            openblas = self.dependencies["openblas"]
            libs = ";".join(self._library_files(openblas, ["openblas"])
                            + openblas.cpp_info.aggregated_components().system_libs)
            tc.cache_variables["BLAS_LIBRARIES"] = libs
            tc.cache_variables["LAPACK_LIBRARIES"] = libs
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _write_cmake_module(self):
        # Most deal.II applications (all its tutorials) call these two macros from
        # upstream's deal.IIConfig.cmake. That file hard-codes the build machine's
        # dependency paths, so it is replaced by the CMakeDeps one plus these
        # equivalents.
        content = textwrap.dedent("""\
            set(DEAL_II_PACKAGE_VERSION "${deal.II_VERSION}")
            set(DEAL_II_VERSION "${deal.II_VERSION}")
            if(NOT COMMAND deal_ii_initialize_cached_variables)
              macro(deal_ii_initialize_cached_variables)
                if(NOT CMAKE_BUILD_TYPE)
                  set(CMAKE_BUILD_TYPE "Release" CACHE STRING "" FORCE)
                endif()
              endmacro()
            endif()
            if(NOT COMMAND deal_ii_setup_target)
              macro(deal_ii_setup_target _target)
                target_link_libraries(${_target} dealii::dealii)
              endmacro()
            endif()
            """)
        save(self, os.path.join(self.package_folder, self._cmake_module), content)

    @property
    def _cmake_module(self):
        return os.path.join("lib", "cmake", "conan-dealii-macros.cmake")

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # Upstream's macros, scripts and summary files belong to its CMake config.
        rmdir(self, os.path.join(self.package_folder, "share"))
        # README.md, LICENSE.md (copied to licenses/ above) and configure's logs.
        for pattern in ("*.md", "*.log", "*.txt"):
            rm(self, pattern, self.package_folder)
        self._write_cmake_module()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "deal.II")
        self.cpp_info.set_property("cmake_target_name", "dealii::dealii")
        self.cpp_info.set_property("cmake_target_aliases", ["dealii::dealii_release", "dealii::dealii_debug"])
        self.cpp_info.set_property("cmake_build_modules", [self._cmake_module])
        self.cpp_info.set_property("pkg_config_name", "deal.II")
        self.cpp_info.libs = ["deal_II.g" if self.settings.build_type == "Debug" else "deal_II"]
        # The bundled libraries' headers (boost, Kokkos, taskflow, ...) are included
        # from deal.II's public headers.
        self.cpp_info.includedirs = ["include", os.path.join("include", "deal.II", "bundled")]
        # As upstream's targets: deal.II's headers switch assertions and some class
        # members on DEBUG, which therefore has to match the library.
        self.cpp_info.defines = ["DEBUG"] if self.settings.build_type == "Debug" else ["NDEBUG"]

        requires = []
        if self.options.with_mpi:
            # Only the MPI C component: the openmpi package as a whole also carries
            # libompitrace, whose PMPI wrappers print a trace line for every MPI call.
            requires.append("openmpi::ompi-c")
        for option, ref in (
            ("with_p4est", "p4est::p4est"),
            ("with_petsc", "petsc::petsc"),
            ("with_metis", "metis::metis"),
            ("with_lapack", "openblas::openblas_component"),
            ("with_zlib", "zlib::zlib"),
        ):
            if self.options.get_safe(option):
                requires.append(ref)
        self.cpp_info.requires = requires

        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "pthread", "dl", "rt"]
