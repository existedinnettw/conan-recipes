import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import collect_libs, copy, get, replace_in_file


class MavsdkConan(ConanFile):
    name = "mavsdk"
    license = "BSD-3-Clause"
    url = "https://github.com/mavlink/MAVSDK"
    homepage = "https://mavsdk.mavlink.io"
    description = "API and library for MAVLink-compatible systems"
    topics = ("mavlink", "drone", "robotics", "px4", "ardupilot")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_curl": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_curl": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "cmake_minimum_required(VERSION 3.22.1)\n",
            "cmake_minimum_required(VERSION 3.22.1)\n\nproject(mavsdk_superbuild)\n",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "\nproject(mavsdk_superbuild)\n\n\nif (BUILD_BACKEND)",
            "\nif (BUILD_BACKEND)",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            'set(VERSION_STR "0.0.0")',
            f'set(VERSION_STR "v{self.version}")',
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SUPERBUILD"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        tc.variables["BUILD_MAVSDK_SERVER"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_FUZZ_TESTS"] = False
        tc.variables["BUILD_WITHOUT_CURL"] = not bool(self.options.with_curl)
        tc.variables["CCACHE"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "MAVSDK")
        self.cpp_info.set_property("cmake_target_name", "MAVSDK::mavsdk")

        if self.options.shared:
            # Upstream's shared object intentionally leaves JsonCpp symbols for
            # the final consumer link, while its superbuild installs JsonCpp
            # alongside MAVSDK.
            self.cpp_info.libs = ["mavsdk", "jsoncpp"]
            self.cpp_info.defines = ["MAVSDK_SHARED"]
        else:
            libraries = collect_libs(self)
            self.cpp_info.libs = ["mavsdk"] + [
                lib for lib in libraries if lib != "mavsdk"
            ]

        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["dl", "pthread", "rt"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32"]
