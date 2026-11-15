import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class Aruco2Conan(ConanFile):
    name = "aruco2"
    description = ("Proposed replacement for OpenCV's ArUco module (based on ArUco Nano): fiducial "
                   "markers, boards, diamonds, fractal and RArUco (recursive) markers")
    license = "Apache-2.0"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/rmsalinas/aruco2"
    topics = ("aruco", "raruco", "fiducial-markers", "computer-vision", "opencv")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {
        "shared": False,
        "fPIC": True,
        # The library uses core, imgproc, flann and calib3d.
        "opencv/*:dnn": False,
        "opencv/*:gapi": False,
        "opencv/*:highgui": False,
        "opencv/*:imgcodecs": False,
        "opencv/*:ml": False,
        "opencv/*:photo": False,
        "opencv/*:stitching": False,
        "opencv/*:video": False,
        "opencv/*:videoio": False,
    }
    exports_sources = "CMakeLists.txt"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("opencv/4.12.0", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)
        opencv = self.dependencies["opencv"].options
        for module in ("imgproc", "flann", "calib3d"):
            if not opencv.get_safe(module):
                raise ConanInvalidConfiguration(f"{self.ref} requires opencv/*:{module}=True")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], destination="aruco2", strip_root=True)
        # highgui is included but not used.
        replace_in_file(self, os.path.join(self.source_folder, "aruco2", "src", "aruco2.cpp"),
                        "#include <opencv2/highgui.hpp>", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ARUCO2_SOURCE_DIR"] = os.path.join(self.source_folder, "aruco2").replace("\\", "/")
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.export_sources_folder)
        cmake.build()

    def package(self):
        copy(self, "LICENSE", os.path.join(self.source_folder, "aruco2"), os.path.join(self.package_folder, "licenses"))
        CMake(self).install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "aruco2")
        self.cpp_info.set_property("cmake_target_name", "aruco2::aruco2")
        self.cpp_info.libs = ["aruco2"]
        self.cpp_info.requires = ["opencv::opencv_core", "opencv::opencv_imgproc", "opencv::opencv_flann",
                                  "opencv::opencv_calib3d"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "pthread"]
