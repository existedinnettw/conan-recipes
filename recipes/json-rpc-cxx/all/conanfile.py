import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class JsonRpcCxxConan(ConanFile):
    name = "json-rpc-cxx"
    description = "JSON-RPC 2.0 client and server framework for modern C++, built on nlohmann/json"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/jsonrpcx/json-rpc-cxx"
    topics = ("json-rpc", "rpc", "json", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("nlohmann_json/[>=3.10.0 <4]", transitive_headers=True)

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "json-rpc-cxx")
        self.cpp_info.set_property("cmake_target_name", "json-rpc-cxx::json-rpc-cxx")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
