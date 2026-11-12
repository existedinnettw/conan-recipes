import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class OpenVinsConan(ConanFile):
    name = "open_vins"
    description = "OpenVINS: an open source MSCKF-based visual-inertial estimator (ROS-free libraries)"
    license = "GPL-3.0-only"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/rpng/open_vins"
    topics = ("vio", "visual-inertial-odometry", "msckf", "slam", "computer-vision", "robotics")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_aruco": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_aruco": True,
        # Conan Center's boost 1.90 builds boost_cobalt_io_ssl with GCC 14, then rejects it
        # in package_info; nothing here uses Cobalt.
        "boost/*:without_cobalt": True,
        # The libraries use core, imgproc, imgcodecs, features2d, video, calib3d and objdetect.
        "opencv/*:dnn": False,
        "opencv/*:gapi": False,
        "opencv/*:highgui": False,
        "opencv/*:ml": False,
        "opencv/*:photo": False,
        "opencv/*:stitching": False,
        "opencv/*:videoio": False,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Public headers include Eigen, OpenCV, Boost and Ceres.
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("opencv/4.12.0", transitive_headers=True, transitive_libs=True)
        self.requires("boost/1.90.0", transitive_headers=True, transitive_libs=True)
        self.requires("ceres-solver/2.2.0", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} recipe is only validated on Linux")
        # Ceres 2.2 headers need C++17.
        check_min_cppstd(self, 17)
        opencv = self.dependencies["opencv"].options
        for module in ("imgproc", "imgcodecs", "features2d", "video", "calib3d"):
            if not opencv.get_safe(module):
                raise ConanInvalidConfiguration(f"{self.ref} requires opencv/*:{module}=True")
        if self.options.with_aruco and not opencv.get_safe("objdetect"):
            raise ConanInvalidConfiguration(f"{self.ref} with_aruco requires opencv/*:objdetect=True")
        boost = self.dependencies["boost"].options
        for lib in ("filesystem", "date_time"):
            if boost.get_safe(f"without_{lib}"):
                raise ConanInvalidConfiguration(f"{self.ref} requires boost/*:without_{lib}=False")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        core = os.path.join(self.source_folder, "ov_core", "src")
        # highgui headers are included but never used; opencv is built without highgui.
        for header in ("track/TrackBase.h", "track/Grider_GRID.h", "track/Grider_FAST.h"):
            replace_in_file(self, os.path.join(core, header), "#include <opencv2/highgui/highgui.hpp>\n", "")
        # Since OpenCV 4.7 ArUco lives in objdetect; opencv2/aruco.hpp is the contrib module.
        replace_in_file(self, os.path.join(core, "track", "TrackAruco.h"),
                        "#include <opencv2/aruco.hpp>", "#include <opencv2/objdetect/aruco_detector.hpp>")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["OPEN_VINS_WITH_ARUCO"] = bool(self.options.with_aruco)
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "open_vins")

        opencv = [
            "opencv::opencv_core",
            "opencv::opencv_imgproc",
            "opencv::opencv_imgcodecs",
            "opencv::opencv_features2d",
            "opencv::opencv_video",
            "opencv::opencv_calib3d",
        ]
        if self.options.with_aruco:
            opencv.append("opencv::opencv_objdetect")

        core = self.cpp_info.components["ov_core"]
        core.set_property("cmake_target_name", "open_vins::ov_core")
        core.libs = ["ov_core_lib"]
        core.includedirs = [os.path.join("include", "open_vins")]
        core.defines = ["ROS_AVAILABLE=0", f"ENABLE_ARUCO_TAGS={int(bool(self.options.with_aruco))}"]
        core.requires = ["eigen::eigen", "boost::filesystem", "boost::date_time", "boost::headers"] + opencv
        core.system_libs = ["pthread", "m"]

        init = self.cpp_info.components["ov_init"]
        init.set_property("cmake_target_name", "open_vins::ov_init")
        init.libs = ["ov_init_lib"]
        init.includedirs = [os.path.join("include", "open_vins")]
        init.requires = ["ov_core", "ceres-solver::ceres-solver"]

        msckf = self.cpp_info.components["ov_msckf"]
        msckf.set_property("cmake_target_name", "open_vins::ov_msckf")
        msckf.libs = ["ov_msckf_lib"]
        msckf.includedirs = [os.path.join("include", "open_vins")]
        msckf.requires = ["ov_init"]

        ov_eval = self.cpp_info.components["ov_eval"]
        ov_eval.set_property("cmake_target_name", "open_vins::ov_eval")
        ov_eval.libs = ["ov_eval_lib"]
        ov_eval.includedirs = [os.path.join("include", "open_vins")]
        ov_eval.requires = ["ov_core"]
