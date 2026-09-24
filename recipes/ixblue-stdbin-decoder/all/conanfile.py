import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, load, replace_in_file, rmdir, save


class IxblueStdbinDecoderConan(ConanFile):
    name = "ixblue-stdbin-decoder"
    description = "iXblue parsing library for the iXblue stdbin inertial navigation protocol"
    license = "MIT"
    url = "https://github.com/ixblue/ixblue_stdbin_decoder"
    homepage = "https://github.com/ixblue/ixblue_stdbin_decoder"
    topics = ("ixblue", "stdbin", "ins", "inertial-navigation", "parser", "protocol")
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

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # The public headers use boost::asio::const_buffer, boost::optional and
        # boost::circular_buffer; all of it is header-only.
        self.requires("boost/[>=1.71 <2]", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 11)
        # Upstream exports no symbols and forces a static build on MSVC.
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} does not support shared builds on Windows")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        # Only header-only Boost libraries are used (Boost.System has been header-only
        # since 1.69), so do not require the compiled system component and link the
        # headers target instead of whatever ${Boost_LIBRARIES} expands to.
        replace_in_file(self, cmakelists,
                        "find_package(Boost REQUIRED COMPONENTS system)",
                        "find_package(Boost REQUIRED)")
        replace_in_file(self, cmakelists,
                        "    $<INSTALL_INTERFACE:include>\n    ${Boost_INCLUDE_DIRS}\n",
                        "    $<INSTALL_INTERFACE:include>\n")
        replace_in_file(self, cmakelists,
                        "  PUBLIC\n    ${Boost_LIBRARIES}\n",
                        "  PUBLIC\n    Boost::headers\n")
        # Honour the profile's compiler.cppstd instead of pinning C++11.
        replace_in_file(self, cmakelists,
                        "  set(CMAKE_CXX_STANDARD 11)\n  set(CMAKE_CXX_STANDARD_REQUIRED ON)\n",
                        "")

        # boost::asio::buffer_cast was removed in Boost 1.87; const_buffer::data()
        # exists since 1.66.
        for relpath in (os.path.join("include", "ixblue_stdbin_decoder", "memory_block_parser.h"),
                        os.path.join("src", "memory_block_parser.cpp")):
            path = os.path.join(self.source_folder, relpath)
            content = load(self, path)
            content = re.sub(r"boost::asio::buffer_cast<(const \w+\*)>\((\w+)\)",
                             r"static_cast<\1>(\2.data())", content)
            save(self, path, content)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(VERSION 3.1), which CMake 4 rejects.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_STDBIN_EXAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # Only the catkin package.xml lands here.
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ixblue_stdbin_decoder")
        self.cpp_info.set_property("cmake_target_name", "ixblue_stdbin_decoder::ixblue_stdbin_decoder")
        self.cpp_info.libs = ["ixblue_stdbin_decoder"]
        self.cpp_info.requires = ["boost::headers"]
