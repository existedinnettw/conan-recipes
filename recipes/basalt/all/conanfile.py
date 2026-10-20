import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, load, replace_in_file, rm, rmdir, save


class BasaltConan(ConanFile):
    name = "basalt"
    description = (
        "Basalt: visual-inertial mapping with non-linear factor recovery; visual-inertial "
        "odometry, mapping and camera/IMU calibration"
    )
    license = "BSD-3-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://gitlab.com/VladyslavUsenko/basalt"
    topics = ("slam", "vio", "visual-inertial-odometry", "calibration", "computer-vision", "robotics")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tools": [True, False],
        "instantiations_double": [True, False],
        "instantiations_float": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tools": True,
        "instantiations_double": True,
        "instantiations_float": True,
        # Conan Center's boost 1.90 builds boost_cobalt_io_ssl with GCC 14, then rejects it
        # in package_info; the bundled rosbag does not use Cobalt.
        "boost/*:without_cobalt": True,
        # onetbb's tbbbind only accepts a shared hwloc.
        "hwloc/*:shared": True,
        # The library uses core, imgproc, features2d, calib3d and imgcodecs.
        "opencv/*:dnn": False,
        "opencv/*:gapi": False,
        "opencv/*:highgui": False,
        "opencv/*:ml": False,
        "opencv/*:objdetect": False,
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
        self.requires("basalt-headers/cci.20260228", transitive_headers=True)
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("onetbb/2022.3.0", transitive_headers=True, transitive_libs=True)
        self.requires("opencv/4.12.0", transitive_headers=True, transitive_libs=True)
        self.requires("fmt/12.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("opengv/cci.20200806")
        self.requires("nlohmann_json/3.12.0")
        self.requires("magic_enum/0.9.7")
        self.requires("cli11/2.6.2")
        # Bundled rosbag storage.
        self.requires("boost/1.90.0")
        self.requires("bzip2/1.0.8")
        self.requires("lz4/1.10.0")
        self.requires("console_bridge/1.0.2")
        if self.options.with_tools:
            self.requires("pangolin/0.9.4")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} recipe is only validated on Linux")
        check_min_cppstd(self, 17)
        if not (self.options.instantiations_double or self.options.instantiations_float):
            raise ConanInvalidConfiguration(f"{self.ref} needs instantiations_double or instantiations_float")
        opencv = self.dependencies["opencv"].options
        for module in ("calib3d", "features2d", "flann", "imgproc", "imgcodecs"):
            if not opencv.get_safe(module):
                raise ConanInvalidConfiguration(f"{self.ref} requires opencv/*:{module}=True")
        boost = self.dependencies["boost"].options
        for lib in ("date_time", "filesystem", "program_options", "regex", "thread"):
            if boost.get_safe(f"without_{lib}"):
                raise ConanInvalidConfiguration(f"{self.ref} requires boost/*:without_{lib}=False")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["basalt"], strip_root=True)
        get(self, **sources["ros_comm"], strip_root=True,
            destination=os.path.join(self.source_folder, "thirdparty", "ros_comm"))
        get(self, **sources["roscpp_core"], strip_root=True,
            destination=os.path.join(self.source_folder, "thirdparty", "roscpp_core"))
        # Upstream's rosbag overlay port (vcpkg/ports/rosbag/cmake/CMakeLists.txt.in) as a
        # subproject: one static library, installed only for static basalt.
        save(self, os.path.join(self.source_folder, "thirdparty", "rosbag", "CMakeLists.txt"), textwrap.dedent("""\
            set(ROS_COMM "${CMAKE_CURRENT_SOURCE_DIR}/../ros_comm")
            set(ROSCPP_CORE "${CMAKE_CURRENT_SOURCE_DIR}/../roscpp_core")

            find_package(BZip2 REQUIRED)
            find_package(console_bridge CONFIG REQUIRED)

            file(GLOB CPP_COMMON_SRCS "${ROSCPP_CORE}/cpp_common/src/*.cpp")
            file(GLOB ROSCPP_SERIALIZATION_SRCS "${ROSCPP_CORE}/roscpp_serialization/src/*.cpp")
            file(GLOB ROSTIME_SRCS "${ROSCPP_CORE}/rostime/src/*.cpp")
            file(GLOB ROSBAG_SRCS "${ROS_COMM}/tools/rosbag_storage/src/*.cpp")
            file(GLOB ROSLZ4_SRCS "${ROS_COMM}/utilities/roslz4/src/[a-z]*.c")

            add_library(rosbag STATIC
              ${ROSBAG_SRCS} ${ROSTIME_SRCS} ${CPP_COMMON_SRCS} ${ROSCPP_SERIALIZATION_SRCS} ${ROSLZ4_SRCS})
            set_target_properties(rosbag PROPERTIES OUTPUT_NAME basalt_rosbag POSITION_INDEPENDENT_CODE ON)
            target_compile_options(rosbag PRIVATE -Wno-unused-parameter -Wno-deprecated-declarations)
            if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
              target_compile_options(rosbag PRIVATE $<$<COMPILE_LANGUAGE:CXX>:-Wno-catch-value>)
            endif()
            target_include_directories(rosbag PUBLIC
              ${ROS_COMM}/tools/rosbag_storage/include
              ${ROSCPP_CORE}/cpp_common/include
              ${ROSCPP_CORE}/rostime/include
              ${ROSCPP_CORE}/roscpp_serialization/include
              ${ROSCPP_CORE}/roscpp_traits/include
              ${ROS_COMM}/utilities/roslz4/include)
            target_link_libraries(rosbag PUBLIC
              Boost::date_time Boost::filesystem Boost::program_options Boost::regex Boost::thread
              Boost::headers BZip2::BZip2 console_bridge::console_bridge lz4::lz4)
        """))

        # The bundled apriltag relied on a vendored basalt-headers include path.
        replace_in_file(self, os.path.join(self.source_folder, "thirdparty", "apriltag", "CMakeLists.txt"),
                        "target_link_libraries(apriltag PUBLIC basalt::opencv Sophus::Sophus)",
                        "target_link_libraries(apriltag PUBLIC basalt::opencv basalt::basalt-headers)")

        top = os.path.join(self.source_folder, "CMakeLists.txt")
        # Portable binaries: no -march=native, and no -Werror in a package build.
        replace_in_file(self, top, 'set(BASALT_MARCH_FLAGS "-march=${CXX_MARCH}")', 'set(BASALT_MARCH_FLAGS "")')
        replace_in_file(self, top, '"-Wall -Wextra -Werror ', '"-Wall -Wextra ')
        # Boost.Format is header-only; Conan's boost has no Boost::format component.
        replace_in_file(self, top,
                        "find_package(Boost CONFIG REQUIRED COMPONENTS date_time filesystem format program_options regex thread)",
                        "find_package(Boost CONFIG REQUIRED COMPONENTS date_time filesystem program_options regex thread)")
        replace_in_file(self, top, "find_package(rosbag CONFIG REQUIRED)\n", "")
        replace_in_file(self, top, "find_package(Pangolin CONFIG REQUIRED)\n",
                        "if(BASALT_BUILD_TOOLS)\n  find_package(Pangolin CONFIG REQUIRED)\nendif()\n")
        replace_in_file(self, top, "find_package(GTest CONFIG REQUIRED)\n", "")
        replace_in_file(self, top, "add_subdirectory(thirdparty/apriltag EXCLUDE_FROM_ALL)",
                        "add_subdirectory(thirdparty/apriltag EXCLUDE_FROM_ALL)\n"
                        "set_target_properties(apriltag PROPERTIES OUTPUT_NAME basalt_apriltag)\n"
                        "add_subdirectory(thirdparty/rosbag EXCLUDE_FROM_ALL)\n"
                        "if(NOT BASALT_BUILD_SHARED_LIB)\n"
                        "  install(TARGETS apriltag rosbag ARCHIVE DESTINATION ${CMAKE_INSTALL_PREFIX}/lib)\n"
                        "endif()")
        # The apps all use Pangolin; the T265 tools need librealsense 2.51 (not packaged).
        replace_in_file(self, top, "add_executable(basalt_calibrate src/calibrate.cpp",
                        "if(BASALT_BUILD_TOOLS)\nadd_executable(basalt_calibrate src/calibrate.cpp")
        replace_in_file(self, top, "find_package(realsense2 QUIET)\nif(realsense2_FOUND)",
                        "if(FALSE)")
        replace_in_file(self, top, "if(realsense2_FOUND)\n    install(", "if(FALSE)\n    install(")
        replace_in_file(self, top, 'file(GLOB SCRIPTS_TO_INSTALL',
                        'endif()\n\nfile(GLOB SCRIPTS_TO_INSTALL')
        replace_in_file(self, top,
                        'install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/data/udev"\n'
                        '  DESTINATION ${CMAKE_INSTALL_PREFIX}/etc/basalt)\n', "")
        replace_in_file(self, top, "add_subdirectory(test)", "")
        # stdc++fs is libstdc++ only; the recipe passes it when the profile uses libstdc++.
        replace_in_file(self, top, "  set(STD_CXX_FS stdc++fs)", "  set(STD_CXX_FS ${BASALT_STD_CXX_FS})")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BASALT_BUILD_SHARED_LIB"] = bool(self.options.shared)
        tc.cache_variables["BASALT_FULLY_STATIC_BINARIES"] = False
        tc.cache_variables["BASALT_BUILD_TOOLS"] = bool(self.options.with_tools)
        tc.cache_variables["BASALT_INSTANTIATIONS_DOUBLE"] = bool(self.options.instantiations_double)
        tc.cache_variables["BASALT_INSTANTIATIONS_FLOAT"] = bool(self.options.instantiations_float)
        tc.cache_variables["CXX_MARCH"] = "unused"
        tc.cache_variables["BASALT_STD_CXX_FS"] = "stdc++fs" if self._uses_libstdcxx else ""
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", os.path.join(self.source_folder, "thirdparty", "apriltag", "ethz_apriltag2"),
             os.path.join(self.package_folder, "licenses", "ethz_apriltag2"))
        # ros_comm and roscpp_core ship no license file; their sources carry the BSD notice.
        for name, source in (("ros_comm", os.path.join("tools", "rosbag_storage", "src", "bag.cpp")),
                             ("roscpp_core", os.path.join("rostime", "src", "time.cpp"))):
            content = load(self, os.path.join(self.source_folder, "thirdparty", name, source))
            notice = content[:content.index("#include")].strip()
            save(self, os.path.join(self.package_folder, "licenses", name, "LICENSE"), notice + "\n")
        cmake = CMake(self)
        cmake.install()
        # Upstream installs no headers. Leave out those needing what the library does not
        # link: the bundled rosbag (dataset_io_rosbag.h), librealsense (rs_t265.h), and
        # Pangolin (calibration GUIs built into the apps, vis_utils.h without the tools).
        include = os.path.join(self.package_folder, "include")
        copy(self, "*.h", os.path.join(self.source_folder, "include"), include)
        copy(self, "*.hpp", os.path.join(self.source_folder, "include"), include)
        for header in ("io/dataset_io_rosbag.h", "device/rs_t265.h",
                       "calibration/cam_calib.h", "calibration/cam_imu_calib.h"):
            rm(self, os.path.basename(header), os.path.join(include, "basalt", os.path.dirname(header)))
        rmdir(self, os.path.join(include, "basalt", "device"))
        if not self.options.with_tools:
            rm(self, "vis_utils.h", os.path.join(include, "basalt", "utils"))

    @property
    def _uses_libstdcxx(self):
        return str(self.settings.compiler.get_safe("libcxx", "")).startswith("libstdc++")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "basalt")
        self.cpp_info.set_property("cmake_target_name", "basalt::basalt")
        self.cpp_info.libs = ["basalt"]
        if not self.options.shared:
            self.cpp_info.libs.extend(["basalt_apriltag", "basalt_rosbag"])
        defines = []
        if self.options.instantiations_double:
            defines.append("BASALT_INSTANTIATIONS_DOUBLE")
        if self.options.instantiations_float:
            defines.append("BASALT_INSTANTIATIONS_FLOAT")
        self.cpp_info.defines = defines
        self.cpp_info.system_libs = ["pthread", "m"]
        if self._uses_libstdcxx:
            self.cpp_info.system_libs.append("stdc++fs")
        self.cpp_info.resdirs = ["etc"]
        self.cpp_info.requires = [
            "basalt-headers::basalt-headers",
            "eigen::eigen",
            "onetbb::libtbb",
            "opencv::opencv_core",
            "opencv::opencv_imgproc",
            "opencv::opencv_features2d",
            "opencv::opencv_calib3d",
            "opencv::opencv_imgcodecs",
            "fmt::fmt",
            "opengv::opengv",
            "nlohmann_json::nlohmann_json",
            "magic_enum::magic_enum",
            "cli11::cli11",
            "boost::date_time",
            "boost::filesystem",
            "boost::program_options",
            "boost::regex",
            "boost::thread",
            "bzip2::bzip2",
            "lz4::lz4",
            "console_bridge::console_bridge",
        ]
        if self.options.with_tools:
            self.cpp_info.requires.append("pangolin::pangolin")
            # A library package's bin/ is not put on PATH by default.
            self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
