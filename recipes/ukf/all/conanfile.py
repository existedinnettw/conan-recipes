import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class UkfConan(ConanFile):
    name = "ukf"
    license = "MIT"
    url = "https://github.com/sfwa/ukf"
    homepage = "https://github.com/sfwa/ukf"
    description = "Header-only Unscented Kalman Filter library for state and parameter estimation"
    topics = ("ukf", "kalman-filter", "estimation", "embedded", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        # UKF/Config.h refuses to compile unless exactly one of
        # UKF_SINGLE_PRECISION / UKF_DOUBLE_PRECISION is defined. None leaves
        # that choice to the consumer, as upstream does.
        "precision": [None, "single", "double"],
    }
    default_options = {
        "precision": None,
    }

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/3.4.0", transitive_headers=True)

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Types.h aliases Eigen::Quaternion but only includes <Eigen/Core>, so
        # the headers only compile if the consumer includes <Eigen/Geometry>
        # first, as upstream's own tests do.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "include", "UKF", "Types.h"),
            "#include <Eigen/Core>",
            "#include <Eigen/Core>\n#include <Eigen/Geometry>",
        )

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(
            self,
            "*.h",
            os.path.join(self.source_folder, "include"),
            os.path.join(self.package_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ukf")
        self.cpp_info.set_property("cmake_target_name", "ukf::ukf")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.options.precision:
            self.cpp_info.defines = [f"UKF_{str(self.options.precision).upper()}_PRECISION"]
