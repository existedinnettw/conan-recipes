import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir, save

required_conan_version = ">=2.0"


class SuperluDistConan(ConanFile):
    name = "superlu_dist"
    description = (
        "SuperLU_DIST: MPI-parallel sparse direct solver for large, unsymmetric linear "
        "systems (supernodal LU factorisation)"
    )
    license = "BSD-3-Clause-LBNL"
    url = "https://github.com/xiaoyeli/superlu_dist"
    homepage = "https://portal.nersc.gov/project/sparse/superlu/"
    topics = ("sparse-direct-solver", "lu-factorization", "linear-algebra", "hpc", "mpi")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_parmetis": [True, False],
        "with_openmp": [True, False],
        # 64-bit int_t (XSDK_INDEX_SIZE=64); ParMETIS/METIS then need 64-bit idx_t too.
        "int64": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_parmetis": True,
        "with_openmp": False,
        "int64": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Open MPI's static archives define the MPI_* entry points as weak symbols,
        # so a shared library linking libmpi.a does not pull them in and is left
        # with undefined MPI symbols plus a partial copy of the profiling wrappers.
        self.options["openmpi"].shared = True
        if self.options.with_parmetis:
            self.options["metis"].with_64bit_types = bool(self.options.int64)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # superlu_ddefs.h and friends include <mpi.h>; the API takes MPI communicators.
        self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        self.requires("openblas/[>=0.3.24 <1]")
        if self.options.with_parmetis:
            self.requires("parmetis/[>=4.0.3 <5]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} is not supported on Windows: no MPI package is available for it"
            )
        if self.options.with_parmetis:
            metis_64 = bool(self.dependencies["metis"].options.with_64bit_types)
            if metis_64 != bool(self.options.int64):
                raise ConanInvalidConfiguration(
                    f"{self.ref} with int64={self.options.int64} requires "
                    f"'-o metis/*:with_64bit_types={self.options.int64}': ParMETIS' idx_t "
                    "has to match SuperLU_DIST's int_t"
                )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _write_project_include(self):
        # Runs right after SuperLU_DIST's project() call. It links MPI::MPI_CXX, which
        # Conan's openmpi only defines for its deprecated C++ bindings; the library
        # only calls the C API. The other find_package() calls create the targets
        # handed over in the TPL_* variables below, which upstream links without
        # looking them up itself.
        content = textwrap.dedent("""\
            find_package(MPI REQUIRED CONFIG)
            if(NOT TARGET MPI::MPI_CXX)
              add_library(MPI::MPI_CXX INTERFACE IMPORTED)
              set_target_properties(MPI::MPI_CXX PROPERTIES INTERFACE_LINK_LIBRARIES MPI::MPI_C)
            endif()
            find_package(OpenBLAS REQUIRED CONFIG)
            """)
        if self.options.with_parmetis:
            content += "find_package(parmetis REQUIRED CONFIG)\n"
        path = os.path.join(self.generators_folder, "conan_superlu_dist_project_include.cmake")
        save(self, path, content)
        return path.replace("\\", "/")

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_SuperLU_DIST_INCLUDE"] = self._write_project_include()
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        # Upstream forces "-O3 -g" into the release flags cache entries.
        tc.cache_variables["CMAKE_C_FLAGS_RELEASE"] = "-O3 -DNDEBUG"
        tc.cache_variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O3 -DNDEBUG"
        tc.cache_variables["XSDK_ENABLE_Fortran"] = False
        tc.cache_variables["enable_python"] = False
        tc.cache_variables["enable_tests"] = False
        tc.cache_variables["enable_examples"] = False
        tc.cache_variables["enable_doc"] = False
        tc.cache_variables["enable_openmp"] = bool(self.options.with_openmp)
        # All three precisions: PETSc's complex scalar build needs complex16.
        tc.cache_variables["enable_single"] = True
        tc.cache_variables["enable_double"] = True
        tc.cache_variables["enable_complex16"] = True
        tc.cache_variables["XSDK_INDEX_SIZE"] = 64 if self.options.int64 else 32
        tc.cache_variables["TPL_ENABLE_INTERNAL_BLASLIB"] = False
        tc.cache_variables["TPL_BLAS_LIBRARIES"] = "OpenBLAS::OpenBLAS"
        tc.cache_variables["TPL_ENABLE_LAPACKLIB"] = False
        tc.cache_variables["TPL_ENABLE_PARMETISLIB"] = bool(self.options.with_parmetis)
        if self.options.with_parmetis:
            parmetis = self.dependencies["parmetis"].cpp_info.aggregated_components()
            tc.cache_variables["TPL_PARMETIS_LIBRARIES"] = "parmetis::parmetis"
            # Upstream only checks this exists and adds it with -I; the include paths
            # really come with the parmetis::parmetis target.
            tc.cache_variables["TPL_PARMETIS_INCLUDE_DIRS"] = parmetis.includedirs[0].replace("\\", "/")
        tc.cache_variables["TPL_ENABLE_COLAMDLIB"] = False
        tc.cache_variables["TPL_ENABLE_COMBBLASLIB"] = False
        tc.cache_variables["TPL_ENABLE_CUDALIB"] = False
        tc.cache_variables["TPL_ENABLE_HIPLIB"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "License.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Upstream's CMake/pkg-config files hard-code build machine paths; CMakeDeps
        # and PkgConfigDeps generate correct ones for consumers instead.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "superlu_dist")
        self.cpp_info.set_property("cmake_target_name", "SuperLU_DIST::superlu_dist")
        self.cpp_info.set_property("pkg_config_name", "superlu_dist")
        self.cpp_info.libs = ["superlu_dist"]
        # Only the MPI C component: the openmpi package as a whole also carries
        # libompitrace, whose PMPI wrappers print a trace line for every MPI call.
        self.cpp_info.requires = ["openmpi::ompi-c", "openblas::openblas_component"]
        if self.options.with_parmetis:
            self.cpp_info.requires.append("parmetis::parmetis")
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
        if self.options.with_openmp:
            openmp_flags = []
            if self.settings.compiler in ("gcc", "clang"):
                openmp_flags = ["-fopenmp"]
            elif self.settings.compiler == "apple-clang":
                openmp_flags = ["-Xpreprocessor", "-fopenmp"]
            self.cpp_info.sharedlinkflags = list(openmp_flags)
            self.cpp_info.exelinkflags = list(openmp_flags)
