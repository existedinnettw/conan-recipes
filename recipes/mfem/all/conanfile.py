import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
    save,
)


class MfemConan(ConanFile):
    name = "mfem"
    description = "MFEM: a free, lightweight, scalable C++ library for finite element methods"
    license = "BSD-3-Clause"
    url = "https://github.com/mfem/mfem"
    homepage = "https://mfem.org"
    topics = ("finite-elements", "fem", "hpc", "pde", "scientific-computing")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_mpi": [True, False],
        "with_zlib": [True, False],
        "with_lapack": [True, False],
        "with_openmp": [True, False],
        "with_simd": [True, False],
        "exceptions": [True, False],
        "thread_safe": [True, False],
        "precision": ["double", "single"],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_mpi": True,
        "with_zlib": True,
        "with_lapack": False,
        "with_openmp": False,
        "with_simd": False,
        "exceptions": False,
        "thread_safe": False,
        "precision": "double",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
            # Parallel MFEM needs hypre, which has no MPI build on Windows.
            self.options.with_mpi = False

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.with_mpi:
            self.options["hypre"].with_mpi = True
            # Open MPI's static archives define the MPI_* entry points as weak symbols,
            # so a shared library linking libmpi.a does not pull them in and is left
            # with undefined MPI symbols plus a partial copy of the profiling wrappers.
            self.options["openmpi"].shared = True

    def requirements(self):
        if self.options.with_mpi:
            # linalg/hypre.hpp is pulled in by mfem.hpp and includes the hypre headers.
            self.requires("hypre/[>=3.2.0 <4]", transitive_headers=True, transitive_libs=True)
            # mfem.hpp includes <mpi.h> and calls MPI from inline code (mfem::Mpi), so
            # consumers have to link MPI themselves.
            self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
            # METIS partitions the serial mesh in ParMesh; used from .cpp files only.
            self.requires("metis/[>=5.2 <6]")
        if self.options.with_zlib:
            # general/zstr.hpp is a public header and includes <zlib.h>.
            self.requires("zlib/[>=1.2.11 <2]", transitive_headers=True)
        if self.options.with_lapack:
            self.requires("openblas/[>=0.3.24 <1]")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)
        if self.options.with_mpi:
            if self.settings.os == "Windows":
                raise ConanInvalidConfiguration(
                    f"{self.ref} with with_mpi=True is not supported on Windows: no MPI "
                    "package is available for it. Use '-o mfem/*:with_mpi=False'."
                )
            if not self.dependencies["hypre"].options.with_mpi:
                raise ConanInvalidConfiguration(
                    f"{self.ref} with with_mpi=True requires '-o hypre/*:with_mpi=True'"
                )
            if self.options.precision == "single":
                # linalg/hypre.hpp: "MFEM_USE_SINGLE=YES requires HYPRE build with
                # --enable-single!", which the hypre recipe does not expose.
                raise ConanInvalidConfiguration(
                    f"{self.ref} with precision=single requires a single precision hypre, "
                    "which is not available. Use '-o mfem/*:with_mpi=False'."
                )
        if self.options.with_lapack and not self.dependencies["openblas"].options.build_lapack:
            raise ConanInvalidConfiguration(
                f"{self.ref} with with_lapack=True requires '-o openblas/*:build_lapack=True'"
            )

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _write_blas_lapack_configs(self):
        # MFEM calls find_package(BLAS/LAPACK REQUIRED), which would reach CMake's
        # FindBLAS/FindLAPACK modules. Those search the machine instead of the Conan
        # dependency graph, and MFEM overwrites CMAKE_MODULE_PATH with its own module
        # directory, so shipping module-mode shims is not an option either. Conan's
        # toolchain prefers config mode, so hand BLAS and LAPACK to CMake as package
        # configs that simply forward to the OpenBLAS target generated by CMakeDeps.
        for name in ("BLAS", "LAPACK"):
            content = textwrap.dedent(f"""\
                find_package(OpenBLAS REQUIRED CONFIG)
                if(NOT TARGET {name}::{name})
                  add_library({name}::{name} INTERFACE IMPORTED)
                  set_target_properties({name}::{name} PROPERTIES
                    INTERFACE_LINK_LIBRARIES OpenBLAS::OpenBLAS)
                endif()
                set({name}_LIBRARIES OpenBLAS::OpenBLAS)
                set({name}_INCLUDE_DIRS "${{OpenBLAS_INCLUDE_DIRS}}")
                set({name}_FOUND TRUE)
                """)
            # Both spellings CMake accepts, so the lookup does not depend on case.
            save(self, os.path.join(self.generators_folder, f"{name}Config.cmake"), content)
            save(self, os.path.join(self.generators_folder, f"{name.lower()}-config.cmake"), content)

    def generate(self):
        deps = CMakeDeps(self)
        if self.options.with_mpi:
            # find_package(METIS) resolves to metis-config.cmake, which by default only
            # spells its variables metis_*, while MFEM collects METIS_LIBRARIES.
            deps.set_property("metis", "cmake_additional_variables_prefixes", ["METIS"])
        deps.generate()
        if self.options.with_lapack:
            self._write_blas_lapack_configs()

        tc = CMakeToolchain(self)
        # MFEM declares its knobs with option()/set(... CACHE ...) under
        # cmake_minimum_required(3.12), i.e. CMP0077 is OLD, so plain variables are
        # ignored: every setting below has to land in the CMake cache.
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["MFEM_USE_MPI"] = bool(self.options.with_mpi)
        # Parallel MFEM partitions meshes with METIS; MFEM ties the two together too.
        tc.cache_variables["MFEM_USE_METIS"] = bool(self.options.with_mpi)
        tc.cache_variables["MFEM_USE_ZLIB"] = bool(self.options.with_zlib)
        tc.cache_variables["MFEM_USE_LAPACK"] = bool(self.options.with_lapack)
        tc.cache_variables["MFEM_USE_OPENMP"] = bool(self.options.with_openmp)
        tc.cache_variables["MFEM_USE_SIMD"] = bool(self.options.with_simd)
        tc.cache_variables["MFEM_USE_EXCEPTIONS"] = bool(self.options.exceptions)
        tc.cache_variables["MFEM_THREAD_SAFE"] = bool(self.options.thread_safe)
        # MFEM_USE_SINGLE/MFEM_USE_DOUBLE are derived from this one and overwritten.
        tc.cache_variables["MFEM_PRECISION"] = str(self.options.precision)
        tc.cache_variables["MFEM_ENABLE_TESTING"] = False
        tc.cache_variables["MFEM_ENABLE_EXAMPLES"] = False
        tc.cache_variables["MFEM_ENABLE_MINIAPPS"] = False
        tc.cache_variables["MFEM_ENABLE_BENCHMARKS"] = False
        # Never let the build reach out to the network for third-party libraries.
        tc.cache_variables["MFEM_FETCH_TPLS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        # Upstream's CMake package files and config.mk hard-code build machine paths
        # and TPL targets; CMakeDeps generates correct ones for consumers instead.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # Only the MPI C component: the openmpi package as a whole also carries
        # libompitrace, whose PMPI wrappers print a trace line for every MPI call.
        requires = []
        if self.options.with_mpi:
            requires += ["hypre::hypre", "openmpi::ompi-c", "metis::metis"]
        if self.options.with_zlib:
            requires.append("zlib::zlib")
        if self.options.with_lapack:
            requires.append("openblas::openblas_component")
        self.cpp_info.requires = requires

        # Upstream installs MFEMConfig.cmake, so consumers write find_package(MFEM).
        self.cpp_info.set_property("cmake_file_name", "MFEM")
        self.cpp_info.set_property("cmake_target_name", "mfem::mfem")
        # Upstream exports the plain, unnamespaced target.
        self.cpp_info.set_property("cmake_target_aliases", ["mfem"])

        self.cpp_info.libs = ["mfem"]

        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "pthread", "rt", "dl"]

        if self.options.with_openmp:
            openmp_flags = []
            if self.settings.compiler in ("gcc", "clang"):
                openmp_flags = ["-fopenmp"]
            elif self.settings.compiler == "apple-clang":
                openmp_flags = ["-Xpreprocessor", "-fopenmp"]
            elif self.settings.compiler == "msvc":
                openmp_flags = ["-openmp"]
            self.cpp_info.cflags += openmp_flags
            self.cpp_info.cxxflags += openmp_flags
            self.cpp_info.sharedlinkflags += openmp_flags
            self.cpp_info.exelinkflags += openmp_flags
