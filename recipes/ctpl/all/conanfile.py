import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CTPLConan(ConanFile):
    name = "ctpl"
    description = "C++ thread pool library (header only)"
    license = "Apache-2.0"
    url = "https://github.com/vit-vit/CTPL"
    homepage = "https://github.com/vit-vit/CTPL"
    topics = ("thread-pool", "threads", "concurrency", "header-only")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        # ctpl.h is the Boost.Lockfree based pool; ctpl_stl.h, the standard library
        # only one, is always installed.
        "with_boost": [True, False],
    }
    default_options = {
        "with_boost": False,
    }
    no_copy_source = True

    def requirements(self):
        if self.options.with_boost:
            self.requires("boost/[>=1.71 <2]", transitive_headers=True, libs=False)

    def package_id(self):
        self.info.settings.clear()

    def validate(self):
        check_min_cppstd(self, 11)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        include = os.path.join(self.package_folder, "include")
        copy(self, "ctpl_stl.h", src=self.source_folder, dst=include)
        if self.options.with_boost:
            copy(self, "ctpl.h", src=self.source_folder, dst=include)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ctpl")
        self.cpp_info.set_property("cmake_target_name", "ctpl::ctpl")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
