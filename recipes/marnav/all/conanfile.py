import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir


class MarnavConan(ConanFile):
    name = "marnav"
    description = (
        "Library for maritime navigation: NMEA-0183 sentences, AIS messages, "
        "SeaTalk and geodesic helpers"
    )
    license = "BSD-4-Clause"
    url = "https://github.com/mariokonrad/marnav"
    homepage = "https://github.com/mariokonrad/marnav"
    topics = ("nmea", "nmea-0183", "ais", "seatalk", "mmsi", "navigation", "maritime")
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

    @property
    def _has_io(self):
        # marnav-io is termios based; upstream only builds it when a test program
        # including <termios.h> compiles.
        return self.settings.os != "Windows"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, 17)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The command line tools pull in the bundled cxxopts and fmt, and the tests the
        # bundled googletest and benchmark; only the libraries are packaged.
        tc.cache_variables["ENABLE_TOOLS"] = False
        tc.cache_variables["ENABLE_EXAMPLES"] = False
        tc.cache_variables["ENABLE_TESTS"] = False
        tc.cache_variables["ENABLE_TESTS_BENCHMARK"] = False
        tc.cache_variables["ENABLE_BENCHMARK"] = False
        tc.cache_variables["ENABLE_PROFILING"] = False
        tc.cache_variables["ENABLE_SANITIZER"] = False
        tc.cache_variables["ENABLE_IWYU"] = False
        # Git is only used to append the commit hash to the version string, which would
        # then depend on whether the build folder happens to sit inside a checkout.
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Git"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        tc.generate()

    def _patch_sources(self):
        # -Werror turns every new compiler warning into a build failure.
        replace_in_file(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"),
                        "\t\t-Werror\n", "")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "marnav")

        postfix = "d" if self.settings.compiler == "msvc" and self.settings.build_type == "Debug" else ""

        self.cpp_info.components["marnav"].set_property("cmake_target_name", "marnav::marnav")
        self.cpp_info.components["marnav"].libs = [f"marnav{postfix}"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.components["marnav"].system_libs = ["m"]

        if self._has_io:
            self.cpp_info.components["marnav-io"].set_property("cmake_target_name", "marnav::marnav-io")
            self.cpp_info.components["marnav-io"].libs = ["marnav-io"]
            self.cpp_info.components["marnav-io"].requires = ["marnav"]
