import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rm, rmdir


class StellaVslamConan(ConanFile):
    name = "stella_vslam"
    description = (
        "stella_vslam: a monocular, stereo and RGBD visual SLAM system supporting "
        "perspective, fisheye and equirectangular cameras"
    )
    license = "BSD-2-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/stella-cv/stella_vslam"
    topics = ("slam", "vslam", "visual-slam", "computer-vision", "robotics", "orb")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_aruco": [True, False],
        "with_openmp": [True, False],
        "deterministic": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_aruco": True,
        "with_openmp": False,
        "deterministic": False,
        # The library itself only uses core, imgproc, features2d, calib3d and objdetect.
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

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("g2o/20230223", transitive_headers=True, transitive_libs=True)
        self.requires("opencv/4.12.0", transitive_headers=True, transitive_libs=True)
        self.requires("yaml-cpp/0.8.0", transitive_headers=True, transitive_libs=True)
        self.requires("spdlog/1.15.3", transitive_headers=True, transitive_libs=True)
        self.requires("nlohmann_json/3.12.0", transitive_headers=True)
        self.requires("sqlite3/3.53.4", transitive_libs=True)

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} recipe is only validated on Linux")
        check_min_cppstd(self, 14)
        if self.options.with_openmp and self.settings.compiler not in ("gcc", "clang"):
            raise ConanInvalidConfiguration(f"{self.ref} with_openmp is only supported with gcc and clang")
        g2o = self.dependencies["g2o"]
        if not g2o.options.with_csparse:
            raise ConanInvalidConfiguration(f"{self.ref} requires g2o/*:with_csparse=True")
        opencv = self.dependencies["opencv"].options
        for module in ("features2d", "calib3d", "flann", "imgproc"):
            if not opencv.get_safe(module):
                raise ConanInvalidConfiguration(f"{self.ref} requires opencv/*:{module}=True")
        if self.options.with_aruco and not opencv.get_safe("objdetect"):
            raise ConanInvalidConfiguration(f"{self.ref} with_aruco requires opencv/*:objdetect=True")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["stella_vslam"], strip_root=True)
        get(self, **sources["fbow"], strip_root=True, destination=os.path.join(self.source_folder, "3rd", "FBoW"))
        get(self, **sources["tinycolormap"], strip_root=True,
            destination=os.path.join(self.source_folder, "3rd", "tinycolormap"))
        rmdir(self, os.path.join(self.source_folder, "3rd", "json"))
        rmdir(self, os.path.join(self.source_folder, "3rd", "spdlog"))

        top = os.path.join(self.source_folder, "CMakeLists.txt")
        # Follow compiler.cppstd from the profile instead of forcing C++11.
        replace_in_file(self, top, "set(CMAKE_CXX_STANDARD 11)\n", "")
        # Use Conan's spdlog unconditionally; the vendored copy is removed above.
        # Request only the OpenCV modules the library uses, so the defaults below suffice.
        replace_in_file(self, top, "core imgcodecs videoio features2d calib3d highgui",
                        "core imgproc features2d calib3d")
        # OpenMP only when with_openmp is set; upstream falls back to a stub OpenMP::OpenMP_CXX.
        replace_in_file(self, top, "find_package(OpenMP REQUIRED)", "find_package(OpenMP)")
        replace_in_file(self, top, "find_package(spdlog QUIET)", "find_package(spdlog REQUIRED CONFIG)")

        lib = os.path.join(self.source_folder, "src", "stella_vslam", "CMakeLists.txt")
        # Use Conan's nlohmann_json instead of the vendored 3.6.1 copy, and do not
        # install json.hpp into the package where it would shadow the consumer's.
        replace_in_file(self, lib,
                        "set(json_INCLUDE_DIR ${PROJECT_SOURCE_DIR}/3rd/json/include)",
                        "find_package(nlohmann_json REQUIRED CONFIG)")
        replace_in_file(self, lib, '"$<BUILD_INTERFACE:${json_INCLUDE_DIR}>"', "")
        replace_in_file(self, lib, '"$<INSTALL_INTERFACE:include/stella_vslam/3rd/json/include>"', "")
        replace_in_file(self, lib,
                        "install(FILES ${json_INCLUDE_DIR}/nlohmann/json.hpp ${json_INCLUDE_DIR}/nlohmann/json_fwd.hpp\n"
                        "        DESTINATION ${STELLA_VSLAM_INCLUDE_INSTALL_DIR}/3rd/json/include/nlohmann)\n",
                        "")
        replace_in_file(self, lib, "                      Eigen3::Eigen\n",
                        "                      Eigen3::Eigen\n                      nlohmann_json::nlohmann_json\n")
        # SQLite3_LIBRARIES is only set by CMake's FindSQLite3, not by CMakeDeps.
        replace_in_file(self, lib, "${SQLite3_LIBRARIES}", "SQLite::SQLite3")

        fbow = os.path.join(self.source_folder, "3rd", "FBoW", "CMakeLists.txt")
        # FBoW links opencv_highgui but never uses it.
        replace_in_file(self, fbow, "        opencv_highgui\n", "")
        # FBoW overwrites the compiler flags, dropping the toolchain's (e.g. -stdlib=libc++); append instead.
        for flags in ("CMAKE_CXX_FLAGS", "CMAKE_CXX_FLAGS_RELEASE", "CMAKE_CXX_FLAGS_DEBUG",
                      "CMAKE_CXX_FLAGS_RELWITHDEBINFO"):
            replace_in_file(self, fbow, f'    set({flags} "', f'    set({flags} "${{{flags}}} ')

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["BOW_FRAMEWORK"] = "FBoW"
        tc.cache_variables["USE_CCACHE"] = False
        tc.cache_variables["USE_SANITIZER"] = False
        tc.cache_variables["BUILD_WITH_MARCH_NATIVE"] = False
        tc.cache_variables["USE_ARUCO"] = bool(self.options.with_aruco)
        tc.cache_variables["USE_OPENMP"] = bool(self.options.with_openmp)
        # Also keeps FBoW, which uses OpenMP whenever it is found, off it.
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = not self.options.with_openmp
        tc.cache_variables["DETERMINISTIC"] = bool(self.options.deterministic)
        tc.cache_variables["USE_GTSAM"] = False
        tc.cache_variables["USE_TRACY"] = False
        tc.cache_variables["USE_CUDA_EFFICIENT_DESCRIPTORS"] = False
        # FBoW: no host-specific AVX/SSE4 flags in a distributable binary.
        for flag in ("USE_AVX", "USE_SSE3", "USE_SSE4"):
            tc.cache_variables[flag] = False
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        for license_file in ("LICENSE", "LICENSE.fork", "LICENSE.original"):
            copy(self, license_file, self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", os.path.join(self.source_folder, "3rd", "FBoW"),
             os.path.join(self.package_folder, "licenses", "FBoW"))
        copy(self, "LICENSE", os.path.join(self.source_folder, "3rd", "tinycolormap"),
             os.path.join(self.package_folder, "licenses", "tinycolormap"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "stella_vslam")

        openmp_flags = ["-fopenmp"] if self.options.with_openmp else []

        fbow = self.cpp_info.components["fbow"]
        fbow.set_property("cmake_target_name", "fbow::fbow")
        fbow.libs = ["fbow"]
        fbow.requires = ["opencv::opencv_core", "opencv::opencv_features2d"]
        fbow.sharedlinkflags = openmp_flags
        fbow.exelinkflags = openmp_flags

        stella = self.cpp_info.components["stella_vslam"]
        stella.set_property("cmake_target_name", "stella_vslam::stella_vslam")
        stella.libs = ["stella_vslam"]
        stella.requires = [
            "fbow",
            "eigen::eigen",
            "nlohmann_json::nlohmann_json",
            "yaml-cpp::yaml-cpp",
            "spdlog::spdlog",
            "sqlite3::sqlite3",
            "opencv::opencv_core",
            "opencv::opencv_features2d",
            "opencv::opencv_calib3d",
            "g2o::core",
            "g2o::stuff",
            "g2o::types_sba",
            "g2o::types_sim3",
            "g2o::solver_dense",
            "g2o::solver_eigen",
            "g2o::solver_csparse",
            "g2o::csparse_extension",
        ]
        defines = ["SPDLOG_ACTIVE_LEVEL=SPDLOG_LEVEL_DEBUG"]
        if self.options.with_aruco:
            stella.requires.append("opencv::opencv_objdetect")
            defines.append("USE_ARUCO")
        if self.options.with_openmp:
            defines.append("USE_OPENMP")
        if self.options.deterministic:
            defines.append("DETERMINISTIC")
        stella.defines = defines
        stella.system_libs = ["pthread", "m"]
        stella.sharedlinkflags = openmp_flags
        stella.exelinkflags = openmp_flags
