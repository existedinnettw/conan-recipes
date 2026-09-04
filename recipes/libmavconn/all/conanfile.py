import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class LibmavconnConan(ConanFile):
    name = "libmavconn"
    license = "BSD-3-Clause, LGPL-3.0-or-later, GPL-3.0-or-later"
    url = "https://github.com/mavlink/mavros"
    homepage = "https://github.com/mavlink/mavros/tree/ros2/libmavconn"
    description = "MAVLink connection and communication library"
    topics = ("mavlink", "drone", "robotics", "serial", "udp")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "CMakeLists.txt", "generated/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("asio/1.38.2")
        self.requires("console_bridge/1.0.2")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 20)

    def layout(self):
        cmake_layout(self)

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(self, **sources["mavros"], strip_root=True)
        get(
            self,
            **sources["mavlink"],
            destination="mavlink-source",
            strip_root=True,
        )
    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("asio", "cmake_file_name", "asio")
        deps.set_property("asio", "cmake_target_name", "asio::asio")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        for license_file in (
            "LICENSE.md",
            "LICENSE-BSD.txt",
            "LICENSE-GPLv3.txt",
            "LICENSE-LGPLv3.txt",
        ):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libmavconn")
        self.cpp_info.set_property("cmake_target_name", "libmavconn::mavconn")
        self.cpp_info.libs = ["mavconn"]
        self.cpp_info.requires = ["asio::asio", "console_bridge::console_bridge"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32"]
