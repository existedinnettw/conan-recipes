import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class LibcanardConan(ConanFile):
    name = "libcanard"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/OpenCyphal/libcanard"
    description = "Compact implementation of the Cyphal/CAN protocol in C for high-integrity real-time embedded systems"
    topics = ("cyphal", "uavcan", "can", "can-fd", "embedded", "real-time")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # False computes the transfer CRC bitwise, saving 512 bytes of ROM.
        "crc_table": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "crc_table": True,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        # CanardCANDLCToLength and CanardCANLengthToDLC are exported data, which a DLL
        # cannot provide without __declspec(dllimport) in canard.h.
        if self.options.shared and self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} exports data symbols and cannot be built as a DLL")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CANARD_CRC_TABLE"] = bool(self.options.crc_table)
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
        self.cpp_info.set_property("cmake_file_name", "libcanard")
        self.cpp_info.set_property("cmake_target_name", "libcanard::canard")
        self.cpp_info.libs = ["canard"]
