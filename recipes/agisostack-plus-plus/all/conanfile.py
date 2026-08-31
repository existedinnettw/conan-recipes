import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class AgIsoStackPlusPlusConan(ConanFile):
    name = "agisostack-plus-plus"
    license = "MIT"
    url = "https://github.com/Open-Agriculture/AgIsoStack-plus-plus"
    homepage = "https://agisostack.com"
    description = "C++ ISO 11783 (ISOBUS) and SAE J1939 CAN stack"
    topics = ("isobus", "iso11783", "j1939", "can", "agriculture")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "can_driver": ["ANY"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "can_driver": "VirtualCAN",
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 14)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["CAN_DRIVER"] = str(self.options.can_driver)
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

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "isobus")

        utility = self.cpp_info.components["Utility"]
        utility.libs = ["Utility"]
        utility.set_property("cmake_target_name", "isobus::Utility")

        isobus = self.cpp_info.components["Isobus"]
        isobus.libs = ["Isobus"]
        isobus.requires = ["Utility"]
        isobus.set_property("cmake_target_name", "isobus::Isobus")

        hardware = self.cpp_info.components["HardwareIntegration"]
        hardware.libs = ["HardwareIntegration"]
        hardware.requires = ["Isobus", "Utility"]
        hardware.set_property("cmake_target_name", "isobus::HardwareIntegration")
        hardware.defines = [
            f"ISOBUS_{driver.strip().upper()}_AVAILABLE"
            for driver in str(self.options.can_driver).split(";")
            if driver.strip()
        ]
        if self.settings.os in ("Linux", "FreeBSD"):
            hardware.system_libs = ["pthread"]
