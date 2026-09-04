import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class ZenohCppConan(ConanFile):
    name = "zenoh-cpp"
    license = "EPL-2.0 OR Apache-2.0"
    url = "https://github.com/eclipse-zenoh/zenoh-cpp"
    homepage = "https://zenoh.io"
    description = "C++ API for Eclipse zenoh"
    topics = ("zenoh", "pub-sub", "query", "distributed-systems", "robotics")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_shared_memory": [True, False],
        "with_unstable_api": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_shared_memory": False,
        "with_unstable_api": False,
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
        source = self.conan_data["sources"][str(self.version)]
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            strip_root=True,
        )
        get(
            self,
            url=source["zenoh_c"]["url"],
            sha256=source["zenoh_c"]["sha256"],
            destination=os.path.join(self.source_folder, "zenoh-c"),
            strip_root=True,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "set(CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake ${CMAKE_MODULE_PATH})",
            "add_subdirectory(zenoh-c)\n"
            "add_subdirectory(zenoh-c/install zenoh-c-install)\n\n"
            "set(CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake ${CMAKE_MODULE_PATH})",
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        tc.variables["ZENOHCXX_ZENOHC"] = True
        tc.variables["ZENOHCXX_ZENOHPICO"] = False
        tc.variables["ZENOHCXX_ENABLE_TESTS"] = False
        tc.variables["ZENOHCXX_ENABLE_EXAMPLES"] = False
        tc.variables["ZENOHC_BUILD_WITH_SHARED_MEMORY"] = bool(
            self.options.with_shared_memory
        )
        tc.variables["ZENOHC_BUILD_WITH_UNSTABLE_API"] = bool(
            self.options.with_unstable_api
        )
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
            dst=os.path.join(self.package_folder, "licenses", "zenoh-cpp"),
        )
        copy(
            self,
            "LICENSE",
            src=os.path.join(self.source_folder, "zenoh-c"),
            dst=os.path.join(self.package_folder, "licenses", "zenoh-c"),
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "zenohcxx")
        self.cpp_info.set_property("cmake_target_name", "zenohcxx::zenohc")
        self.cpp_info.libs = ["zenohc"]
        self.cpp_info.defines = ["ZENOHCXX_ZENOHC"]

        if self.options.shared:
            self.cpp_info.defines.append("ZENOHC_DYN_LIB")
        elif self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["rt", "pthread", "m", "dl"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = [
                "ws2_32", "crypt32", "secur32", "bcrypt", "ncrypt",
                "userenv", "ntdll", "iphlpapi", "runtimeobject",
            ]
        elif self.settings.os == "Macos":
            self.cpp_info.frameworks = ["Foundation", "Security"]
