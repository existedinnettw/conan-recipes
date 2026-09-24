import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class LibnmeaConan(ConanFile):
    name = "libnmea"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/jacketizer/libnmea"
    description = "Lightweight C library for parsing NMEA 0183 sentences"
    topics = ("nmea", "nmea-0183", "gps", "gnss", "parser", "embedded")
    package_type = "library"

    _parsers = ("gpgga", "gpgll", "gpgsa", "gpgsv", "gprmc", "gptxt", "gpvtg")

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # One switch per sentence parser, so firmware builds can drop the ones
        # they never receive.
        **{f"with_{parser}": [True, False] for parser in _parsers},
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        **{f"with_{parser}": True for parser in _parsers},
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

    @property
    def _enabled_parsers(self):
        return [p for p in self._parsers if self.options.get_safe(f"with_{p}")]

    def validate(self):
        # nmea.c registers the parsers from an __attribute__((constructor)).
        if self.settings.compiler == "msvc":
            raise ConanInvalidConfiguration(f"{self.ref} requires GCC-style constructor attributes, which MSVC lacks")
        if not self._enabled_parsers:
            raise ConanInvalidConfiguration(f"{self.ref} needs at least one with_<parser> option enabled")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["LIBNMEA_PARSERS"] = ";".join(self._enabled_parsers)
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
        self.cpp_info.set_property("cmake_file_name", "libnmea")
        self.cpp_info.set_property("cmake_target_name", "libnmea::nmea")
        self.cpp_info.set_property("pkg_config_name", "libnmea")
        self.cpp_info.libs = ["nmea"]
