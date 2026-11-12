import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ArucoNanoConan(ConanFile):
    name = "aruco_nano"
    description = "Minimalist, header-only, high-performance ArUco marker detection on top of OpenCV"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/rmsalinas/aruco_nano"
    topics = ("aruco", "fiducial-markers", "computer-vision", "opencv", "header-only")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    default_options = {
        # The header only uses core, imgproc, calib3d and objdetect.
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
    no_copy_source = True

    def requirements(self):
        self.requires("opencv/4.12.0", transitive_headers=True, transitive_libs=True)

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 17)
        opencv = self.dependencies["opencv"].options
        for module in ("imgproc", "calib3d", "objdetect"):
            if not opencv.get_safe(module):
                raise ConanInvalidConfiguration(f"{self.ref} requires opencv/*:{module}=True")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "aruco_nano.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "aruco_nano")
        self.cpp_info.set_property("cmake_target_name", "aruco_nano::aruco_nano")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.requires = [
            "opencv::opencv_core",
            "opencv::opencv_imgproc",
            "opencv::opencv_calib3d",
            "opencv::opencv_objdetect",
        ]
