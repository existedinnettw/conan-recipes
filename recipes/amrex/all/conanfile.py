import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir, save

required_conan_version = ">=2.0"


class AmrexConan(ConanFile):
    name = "amrex"
    description = (
        "AMReX: a software framework for massively parallel, block-structured adaptive "
        "mesh refinement (AMR) applications"
    )
    license = "BSD-3-Clause-LBNL"
    url = "https://github.com/AMReX-Codes/amrex"
    homepage = "https://amrex-codes.github.io/amrex/"
    topics = ("amr", "adaptive-mesh-refinement", "pde", "hpc", "mpi", "cfd")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # One library per dimension (amrex_1d, amrex_2d, amrex_3d); any combination.
        "with_1d": [True, False],
        "with_2d": [True, False],
        "with_3d": [True, False],
        "precision": ["double", "single"],
        "particles_precision": ["double", "single"],
        "with_mpi": [True, False],
        "with_openmp": [True, False],
        "with_eb": [True, False],
        "with_particles": [True, False],
        "with_linear_solvers": [True, False],
        "with_amrlevel": [True, False],
        "with_hypre": [True, False],
        "tiny_profile": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_1d": False,
        "with_2d": False,
        "with_3d": True,
        "precision": "double",
        "particles_precision": "double",
        "with_mpi": True,
        "with_openmp": False,
        "with_eb": False,
        "with_particles": True,
        "with_linear_solvers": True,
        "with_amrlevel": True,
        "with_hypre": False,
        "tiny_profile": False,
    }

    @property
    def _dims(self):
        return [d for d in (1, 2, 3) if self.options.get_safe(f"with_{d}d")]

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_particles:
            self.options.rm_safe("particles_precision")
        if self.options.with_mpi:
            # Open MPI's static archives define the MPI_* entry points as weak symbols,
            # so a shared library linking libmpi.a does not pull them in and is left
            # with undefined MPI symbols plus a partial copy of the profiling wrappers.
            self.options["openmpi"].shared = True
        if self.options.with_hypre:
            self.options["hypre"].with_mpi = bool(self.options.with_mpi)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_mpi:
            # AMReX_ccse-mpi.H includes <mpi.h> from public headers, and AMReX's own
            # targets link MPI publicly.
            self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        if self.options.with_hypre:
            # AMReX_HypreABecLap*.H and friends include the hypre headers.
            self.requires("hypre/[>=3.2.0 <4]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            # AMReX's targets require cxx_std_20 (Tools/CMake/AMReX_Config.cmake).
            check_min_cppstd(self, 20)
        if not self._dims:
            raise ConanInvalidConfiguration(
                f"{self.ref} needs at least one of with_1d, with_2d, with_3d"
            )
        if self.options.with_mpi and self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} with with_mpi=True is not supported on Windows: no MPI package "
                "is available for it. Use '-o amrex/*:with_mpi=False'."
            )
        if self.options.with_hypre:
            if not self.options.with_linear_solvers:
                raise ConanInvalidConfiguration(
                    f"{self.ref} with with_hypre=True requires with_linear_solvers=True"
                )
            if bool(self.dependencies["hypre"].options.with_mpi) != bool(self.options.with_mpi):
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires hypre/*:with_mpi to match amrex/*:with_mpi"
                )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _write_project_include(self):
        # Runs right after AMReX's project() call, before any of its find_package()
        # calls, to adapt the targets CMakeDeps generates to the names AMReX links.
        content = ""
        if self.options.with_mpi:
            # AMReX links MPI::MPI_CXX, which Conan's openmpi only defines for its
            # (deprecated) C++ bindings. AMReX only uses the C API, so MPI::MPI_C is
            # what it really needs.
            content += textwrap.dedent("""\
                find_package(MPI REQUIRED CONFIG)
                if(NOT TARGET MPI::MPI_CXX)
                  add_library(MPI::MPI_CXX INTERFACE IMPORTED)
                  set_target_properties(MPI::MPI_CXX PROPERTIES
                    INTERFACE_LINK_LIBRARIES MPI::MPI_C)
                endif()
                """)
        if self.options.with_hypre:
            # AMReX's FindHYPRE creates a plain "HYPRE" target; CMakeDeps names it
            # HYPRE::HYPRE.
            content += textwrap.dedent("""\
                find_package(HYPRE REQUIRED CONFIG)
                if(NOT TARGET HYPRE)
                  add_library(HYPRE INTERFACE IMPORTED)
                  set_target_properties(HYPRE PROPERTIES
                    INTERFACE_LINK_LIBRARIES HYPRE::HYPRE)
                endif()
                """)
        path = os.path.join(self.generators_folder, "conan_amrex_project_include.cmake")
        save(self, path, content)
        return path

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_AMReX_INCLUDE"] = self._write_project_include().replace("\\", "/")
        tc.cache_variables["AMReX_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["AMReX_PIC"] = bool(self.options.get_safe("fPIC", True))
        tc.cache_variables["AMReX_SPACEDIM"] = ";".join(str(d) for d in self._dims)
        tc.cache_variables["AMReX_PRECISION"] = str(self.options.precision).upper()
        tc.cache_variables["AMReX_MPI"] = bool(self.options.with_mpi)
        tc.cache_variables["AMReX_OMP"] = bool(self.options.with_openmp)
        tc.cache_variables["AMReX_EB"] = bool(self.options.with_eb)
        tc.cache_variables["AMReX_PARTICLES"] = bool(self.options.with_particles)
        if self.options.with_particles:
            tc.cache_variables["AMReX_PARTICLES_PRECISION"] = str(self.options.particles_precision).upper()
        tc.cache_variables["AMReX_LINEAR_SOLVERS"] = bool(self.options.with_linear_solvers)
        tc.cache_variables["AMReX_AMRLEVEL"] = bool(self.options.with_amrlevel)
        tc.cache_variables["AMReX_HYPRE"] = bool(self.options.with_hypre)
        tc.cache_variables["AMReX_TINY_PROFILE"] = bool(self.options.tiny_profile)
        # Pure C++ build; the Fortran interfaces would need a Fortran compiler.
        tc.cache_variables["AMReX_FORTRAN"] = False
        tc.cache_variables["AMReX_FORTRAN_INTERFACES"] = False
        tc.cache_variables["AMReX_GPU_BACKEND"] = "NONE"
        tc.cache_variables["AMReX_ENABLE_TESTS"] = False
        tc.cache_variables["AMReX_PLOTFILE_TOOLS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        for license_file in ("LICENSE", "NOTICE"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )
        cmake = CMake(self)
        cmake.install()
        # Upstream's CMake package files hard-code build machine paths; CMakeDeps
        # generates correct ones for consumers instead.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        # Build helper scripts and the typechecker, which are of no use to consumers.
        rmdir(self, os.path.join(self.package_folder, "share"))
        # libamrex.so/.a is a legacy symlink to the last dimension's library.
        rm(self, "libamrex.*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "AMReX")
        # Upstream defines no target for "all dimensions"; consumers pick one.
        self.cpp_info.set_property("cmake_target_name", "AMReX::amrex_all_dims")

        requires = []
        if self.options.with_mpi:
            # Only the MPI C component: the openmpi package as a whole also carries
            # libompitrace, whose PMPI wrappers print a trace line for every MPI call.
            requires.append("openmpi::ompi-c")
        if self.options.with_hypre:
            requires.append("hypre::hypre")

        system_libs = []
        if self.settings.os in ("Linux", "FreeBSD"):
            system_libs = ["m", "pthread", "dl"]

        for dim in self._dims:
            component = self.cpp_info.components[f"amrex_{dim}d"]
            component.set_property("cmake_target_name", f"AMReX::amrex_{dim}d")
            component.libs = [f"amrex_{dim}d"]
            # AMReX_Config.H dispatches on AMREX_SPACEDIM to the matching
            # AMReX_Config_<N>D.H, so the dimension has to come with the target.
            component.defines = [f"AMREX_SPACEDIM={dim}"]
            component.requires = list(requires)
            component.system_libs = list(system_libs)
            if self.options.with_openmp:
                openmp_flags = []
                if self.settings.compiler in ("gcc", "clang"):
                    openmp_flags = ["-fopenmp"]
                elif self.settings.compiler == "apple-clang":
                    openmp_flags = ["-Xpreprocessor", "-fopenmp"]
                elif self.settings.compiler == "msvc":
                    openmp_flags = ["-openmp"]
                component.cxxflags = list(openmp_flags)
                component.sharedlinkflags = list(openmp_flags)
                component.exelinkflags = list(openmp_flags)

        # AMReX::amrex is upstream's alias for the last dimension in the list.
        legacy = self.cpp_info.components["amrex"]
        legacy.set_property("cmake_target_name", "AMReX::amrex")
        legacy.requires = [f"amrex_{self._dims[-1]}d"]
