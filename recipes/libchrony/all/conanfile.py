import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"


class LibchronyConan(ConanFile):
    name = "libchrony"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://gitlab.com/chrony/libchrony"
    description = "C library for monitoring chronyd over its Unix domain or UDP command socket"
    topics = ("chrony", "chronyd", "ntp", "time-sync", "monitoring")
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
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        # socket.c uses Unix domain sockets and POSIX headers only.
        if self.settings.os in ("Windows", "baremetal"):
            raise ConanInvalidConfiguration(f"{self.ref} needs POSIX sockets, which {self.settings.os} lacks")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libchrony")
        self.cpp_info.set_property("cmake_target_name", "libchrony::libchrony")
        self.cpp_info.set_property("pkg_config_name", "libchrony")
        self.cpp_info.libs = ["chrony"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
