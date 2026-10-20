import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BasaltHeadersConan(ConanFile):
    name = "basalt-headers"
    description = (
        "Reusable header-only components of Basalt: camera models, image pyramids, "
        "uniform B-splines on Rd/SO(3)/SE(3), IMU preintegration and calibration types"
    )
    license = "BSD-3-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://gitlab.com/VladyslavUsenko/basalt-headers"
    topics = ("slam", "vio", "camera-models", "spline", "imu", "header-only")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    default_options = {
        # basalt links fmt itself; keep Sophus off Conan Center's older fmt.
        "sophus/*:with_fmt": False,
    }
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("sophus/1.22.10", transitive_headers=True)
        self.requires("cereal/1.3.2", transitive_headers=True)

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        copy(self, "*.hpp", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "basalt-headers")
        self.cpp_info.set_property("cmake_target_name", "basalt::basalt-headers")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.requires = ["eigen::eigen", "sophus::sophus", "cereal::cereal"]
