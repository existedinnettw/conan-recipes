import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class CanopenStackConan(ConanFile):
    name = "canopen-stack"
    license = "Apache-2.0"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/embedded-office/canopen-stack"
    description = "Free CANopen stack for embedded devices (CiA 301 / CiA 305) written in C"
    topics = ("canopen", "can", "embedded", "industrial-automation")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    # The *_n and with_* options map to the compile-time defaults in co_cfg.h. They size
    # public structs, so they are propagated to consumers as preprocessor defines.
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "ssdo_n": ["ANY"],
        "csdo_n": ["ANY"],
        "emcy_n": ["ANY"],
        "rpdo_n": ["ANY"],
        "tpdo_n": ["ANY"],
        "with_lss": [True, False],
        "with_csdo": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "ssdo_n": 1,
        "csdo_n": 1,
        "emcy_n": 32,
        "rpdo_n": 4,
        "tpdo_n": 4,
        "with_lss": True,
        "with_csdo": True,
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

    def _config_defines(self):
        return {
            "CO_SSDO_N": self.options.ssdo_n,
            "CO_CSDO_N": self.options.csdo_n,
            "CO_EMCY_N": self.options.emcy_n,
            "CO_RPDO_N": self.options.rpdo_n,
            "CO_TPDO_N": self.options.tpdo_n,
            "USE_LSS": 1 if self.options.with_lss else 0,
            "USE_CSDO": 1 if self.options.with_csdo else 0,
        }

    def validate(self):
        # The default callbacks are __attribute__((weak)) so the application can
        # override them, which MSVC does not support.
        if self.settings.compiler == "msvc":
            raise ConanInvalidConfiguration(f"{self.ref} relies on __attribute__((weak)), unsupported by MSVC")
        # Without exported symbols a DLL is unusable, and applications cannot
        # override the weak callbacks across a DLL boundary.
        if self.options.shared and self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} does not export symbols and cannot be built as a DLL")
        for name in ("ssdo_n", "csdo_n", "emcy_n", "rpdo_n", "tpdo_n"):
            value = str(self.options.get_safe(name))
            if not value.isdigit():
                raise ConanInvalidConfiguration(f"{self.ref} option {name} must be a non-negative integer, got '{value}'")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        for define, value in self._config_defines().items():
            tc.cache_variables[define] = str(value)
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
        self.cpp_info.set_property("cmake_file_name", "canopen-stack")
        self.cpp_info.set_property("cmake_target_name", "canopen-stack::canopen-stack")
        self.cpp_info.libs = ["canopen-stack"]
        self.cpp_info.includedirs = [os.path.join("include", "canopen-stack")]
        self.cpp_info.defines = [f"{define}={value}" for define, value in self._config_defines().items()]
