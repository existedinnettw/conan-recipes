import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class DronecanLibcanardConan(ConanFile):
    name = "dronecan-libcanard"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/dronecan/libcanard"
    description = "DroneCAN (UAVCAN v0) implementation in C for resource-constrained systems"
    topics = ("dronecan", "uavcan", "can", "can-fd", "ardupilot", "embedded")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # The next three change the layout of the structures in canard.h, so they
        # are part of the package_id and are propagated as compile definitions.
        "enable_canfd": [True, False],
        "multi_iface": [True, False],
        "enable_deadline": [True, False],
        "with_socketcan": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_canfd": False,
        "multi_iface": False,
        "enable_deadline": False,
        "with_socketcan": True,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        if self.settings.os != "Linux":
            self.options.rm_safe("with_socketcan")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.options.get_safe("with_socketcan") and self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} SocketCAN driver is Linux-only")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CANARD_ENABLE_CANFD"] = bool(self.options.enable_canfd)
        tc.cache_variables["CANARD_MULTI_IFACE"] = bool(self.options.multi_iface)
        tc.cache_variables["CANARD_ENABLE_DEADLINE"] = bool(self.options.enable_deadline)
        tc.cache_variables["CANARD_WITH_SOCKETCAN"] = bool(self.options.get_safe("with_socketcan"))
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dronecan-libcanard")
        self.cpp_info.set_property("cmake_target_name", "dronecan-libcanard::canard")
        self.cpp_info.libs = ["canard"]
        for option, define in (
            ("enable_canfd", "CANARD_ENABLE_CANFD"),
            ("multi_iface", "CANARD_MULTI_IFACE"),
            ("enable_deadline", "CANARD_ENABLE_DEADLINE"),
        ):
            if self.options.get_safe(option):
                self.cpp_info.defines.append(f"{define}=1")
