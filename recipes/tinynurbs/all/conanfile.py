import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TinynurbsConan(ConanFile):
    name = "tinynurbs"
    description = "Lightweight header-only C++14 library for NURBS curves and surfaces"
    license = "BSD-3-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/pradeep-pyro/tinynurbs"
    topics = ("nurbs", "spline", "curve", "surface", "geometry", "header-only")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def requirements(self):
        # Upstream bundles GLM as a git submodule; use the Conan one instead.
        self.requires("glm/[>=1.0.1 <2]", transitive_headers=True)

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 14)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tinynurbs")
        self.cpp_info.set_property("cmake_target_name", "tinynurbs::tinynurbs")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
