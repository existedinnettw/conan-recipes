import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class PiBemConan(ConanFile):
    name = "pi-bem"
    description = (
        "pi-BEM: parallel boundary element solver for the Laplace equation, with fast "
        "multipole acceleration and CAD-aware refinement, built on deal.II"
    )
    license = "LGPL-2.1-or-later"
    url = "https://github.com/mathLab/pi-BEM"
    homepage = "https://github.com/mathLab/pi-BEM"
    topics = ("bem", "boundary-element-method", "fmm", "laplace", "potential-flow", "mpi", "dealii")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    default_options = {
        # pi-BEM's linear algebra is Trilinos' (Epetra) and its geometry handling uses
        # OpenCASCADE, both through deal.II; its fast multipole code calls TBB, which
        # it gets from deal.II too.
        "dealii/*:with_mpi": True,
        "dealii/*:with_trilinos": True,
        "dealii/*:with_opencascade": True,
        "dealii/*:with_tbb": True,
        "dealii/*:with_metis": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("dealii/[>=9.6 <10]")

    def validate(self):
        check_min_cppstd(self, 17)
        dealii = self.dependencies["dealii"].options
        for option in ("with_mpi", "with_trilinos", "with_opencascade", "with_tbb", "with_metis"):
            if not dealii.get_safe(option):
                raise ConanInvalidConfiguration(f"{self.ref} requires '-o dealii/*:{option}=True'")
        if dealii.int64:
            raise ConanInvalidConfiguration(f"{self.ref} requires '-o dealii/*:int64=False'")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # The linker resolves the libraries that the shared dependencies need (such
        # as PETSc's SuperLU_DIST) through their run environment.
        VirtualRunEnv(self).generate(scope="build")
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Upstream builds its targets only for the build type deal.II was built with,
        # by name.
        tc.cache_variables["CMAKE_BUILD_TYPE"] = "Debug" if self.settings.build_type == "Debug" else "Release"
        # The tests use deal.II's test-suite macros.
        tc.cache_variables["BEM_ENABLE_TESTING"] = False
        # Upstream has no install rules; the programs are copied into bin/ next to
        # their library in lib/.
        tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        # A toolchain variable, not a cache one: those are passed on a shell command
        # line, which would expand $ORIGIN.
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib" if self.settings.os != "Macos" else "@loader_path/../lib"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        for pattern in ("bem_fma_2d*", "bem_fma_3d*"):
            copy(self, pattern, src=self.build_folder, dst=os.path.join(self.package_folder, "bin"),
                 keep_path=False)
        for pattern in ("libbem_fma-lib*.so*", "libbem_fma-lib*.dylib"):
            copy(self, pattern, src=self.build_folder, dst=os.path.join(self.package_folder, "lib"),
                 keep_path=False)
        # The meshes the default parameter files refer to (as ../grids/<name>), plus
        # the NACA wing meshes and CAD files of upstream's examples.
        for folder in ("grids", "NACA_FILES", "NACA_CAD_FILES"):
            copy(self, "*", src=os.path.join(self.source_folder, folder),
                 dst=os.path.join(self.package_folder, "share", "pi-bem", folder))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.define_path("PI_BEM_GRIDS", os.path.join(self.package_folder, "share", "pi-bem", "grids"))
