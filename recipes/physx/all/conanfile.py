import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file

required_conan_version = ">=2.0"


class PhysXConan(ConanFile):
    name = "physx"
    description = "NVIDIA PhysX SDK 5, a scalable multi-platform physics simulation engine (CPU source build)"
    license = "BSD-3-Clause"
    url = "https://github.com/NVIDIA-Omniverse/PhysX"
    homepage = "https://nvidia-omniverse.github.io/PhysX"
    topics = ("physics", "physics-engine", "simulation", "game-development", "robotics")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        # The recipe drives PhysX's CMake directly (no packman/generate_projects); only
        # the Linux platform files have been wired up and tested.
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} recipe only supports Linux")
        if self.settings.arch not in ("x86_64", "armv8"):
            raise ConanInvalidConfiguration(f"{self.ref} only supports x86_64 and armv8")
        # PhysX has its own debug/checked/profile/release configurations; only Debug and
        # Release match one of them.
        if self.settings.build_type not in ("Debug", "Release"):
            raise ConanInvalidConfiguration(f"{self.ref} only supports build_type Debug and Release")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

        linux_cmake = os.path.join(self.source_folder, "physx", "source", "compiler", "cmake", "linux", "CMakeLists.txt")
        # Warnings of newer compilers than NVIDIA's must not fail the build.
        replace_in_file(self, linux_cmake, "-Wall -Werror", "-Wall")
        replace_in_file(self, linux_cmake, "-Weverything", "")
        # PhysX forces C++11 through CMAKE_CXX_FLAGS; let the profile's cppstd decide.
        replace_in_file(self, linux_cmake, "-std=c++11 ", "", strict=False)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["PHYSX_ROOT_DIR"] = os.path.join(self.source_folder, "physx").replace("\\", "/")
        tc.cache_variables["TARGET_BUILD_PLATFORM"] = "linux"
        tc.cache_variables["PX_OUTPUT_ARCH"] = "arm" if self.settings.arch == "armv8" else "x86"
        tc.cache_variables["PX_OUTPUT_LIB_DIR"] = self.build_folder.replace("\\", "/")
        tc.cache_variables["PX_OUTPUT_BIN_DIR"] = self.build_folder.replace("\\", "/")
        tc.cache_variables["PX_GENERATE_STATIC_LIBRARIES"] = not self.options.shared
        tc.cache_variables["PX_BUILDSNIPPETS"] = False
        tc.cache_variables["PX_BUILDPVDRUNTIME"] = False
        tc.cache_variables["PX_CMAKE_SUPPRESS_REGENERATION"] = False
        # The GPU simulation library (libPhysXGpu_64.so) is a closed-source binary that
        # generate_projects.sh pulls with packman; it is not packaged, so skip its copy.
        tc.cache_variables["GPU_LIB_COPIED"] = True
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "physx", "compiler", "public"))
        cmake.build()

    def package(self):
        physx_root = os.path.join(self.source_folder, "physx")
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # include/PxConfig.h is generated into the source tree at configure time.
        copy(self, "*.h", os.path.join(physx_root, "include"), os.path.join(self.package_folder, "include"))
        for lib_dir in glob.glob(os.path.join(self.build_folder, "bin", "*", str(self.settings.build_type).lower())):
            copy(self, "*.a", lib_dir, os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.so", lib_dir, os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PhysX")
        self.cpp_info.set_property("cmake_target_name", "PhysX::PhysXSDK")

        # PhysXFoundation, PhysXCommon, PhysX and PhysXCooking become shared libraries
        # with shared=True; the other libraries are always static.
        shared_libs = ("PhysXFoundation", "PhysXCommon", "PhysX", "PhysXCooking")

        def _add(component, lib, requires, system_libs=()):
            suffix = "_64" if self.options.shared and lib in shared_libs else "_static_64"
            c = self.cpp_info.components[component]
            c.set_property("cmake_target_name", f"PhysX::{lib}")
            c.libs = [f"{lib}{suffix}"]
            c.requires = list(requires)
            c.system_libs = list(system_libs)
            if not self.options.shared:
                c.defines = ["PX_PHYSX_STATIC_LIB"]

        _add("physxfoundation", "PhysXFoundation", [], ["m", "pthread", "rt", "dl"])
        _add("physxcommon", "PhysXCommon", ["physxfoundation"], ["m"])
        _add("physxpvdsdk", "PhysXPvdSDK", ["physxfoundation"])
        if not self.options.shared and self.settings.build_type == "Debug":
            # With PVD (Debug), static PhysXPvdSDK calls PxSetPhysXGpuProfilerCallback from
            # libPhysX, which itself needs PhysXPvdSDK; components cannot express that cycle.
            pull = ["-Wl,-u,PxSetPhysXGpuProfilerCallback"]
            self.cpp_info.components["physxpvdsdk"].exelinkflags = pull
            self.cpp_info.components["physxpvdsdk"].sharedlinkflags = pull
        _add("physxmain", "PhysX", ["physxpvdsdk", "physxcommon", "physxfoundation"], ["m", "dl"])
        _add("physxcooking", "PhysXCooking", ["physxcommon", "physxfoundation"], ["m"])
        _add("physxextensions", "PhysXExtensions", ["physxmain", "physxpvdsdk", "physxcommon", "physxfoundation"])
        _add("physxcharacterkinematic", "PhysXCharacterKinematic", ["physxextensions", "physxcommon", "physxfoundation"])
        _add("physxvehicle", "PhysXVehicle", ["physxextensions", "physxpvdsdk", "physxfoundation"])
        _add("physxvehicle2", "PhysXVehicle2", ["physxextensions", "physxfoundation"])
