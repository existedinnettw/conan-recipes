import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.scm import Version


class KdlParserConan(ConanFile):
    name = "kdl_parser"
    license = "BSD-3-Clause"
    url = "https://github.com/ros/kdl_parser"
    homepage = "http://wiki.ros.org/kdl_parser"
    description = "Construct a KDL tree from an XML robot representation in URDF"
    topics = ("kdl", "urdf", "robotics", "kinematics", "ros")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "CMakeLists.txt"

    @property
    def _is_ros2(self):
        # 3.x is the ament/ROS 2 rewrite: the TinyXML documents disappeared from
        # the public header and the sources moved to the repository root.
        return Version(self.version) >= "2.0"

    @property
    def _source_subfolder(self):
        # 1.x holds both kdl_parser and kdl_parser_py in the repository; only the
        # C++ package is built here. 3.x is extracted into the same place so that
        # the CMakeLists.txt of this recipe fits both layouts.
        return "kdl_parser"

    @property
    def _min_cppstd(self):
        return 17 if self._is_ros2 else 14

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self._is_ros2:
            # treeFromXml() streams a TiXmlDocument into a std::stringstream, which
            # TinyXML only declares when it is built with STL support.
            self.options["tinyxml"].with_stl = True

    def requirements(self):
        # KDL::Tree and urdf::ModelInterface appear in kdl_parser.hpp for every
        # version; 1.x additionally exposes both TinyXML document types.
        self.requires("orocos-kdl/[>=1.5.2 <2]", transitive_headers=True, transitive_libs=True)
        self.requires("urdfdom/[>=3.1.1 <5]", transitive_headers=True, transitive_libs=True)
        if not self._is_ros2:
            self.requires("tinyxml/2.6.2", transitive_headers=True, transitive_libs=True)
            self.requires("tinyxml2/10.0.0", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
            destination=self._source_subfolder if self._is_ros2 else ".",
        )

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        tc.variables["KDL_PARSER_CXX_STANDARD"] = self._min_cppstd
        tc.variables["KDL_PARSER_WITH_TINYXML"] = not self._is_ros2
        # 3.x stopped building check_kdl_parser and left the tool unmaintained,
        # so it no longer compiles.
        tc.variables["KDL_PARSER_BUILD_TOOL"] = not self._is_ros2
        if not self.options.shared:
            tc.preprocessor_definitions["KDL_PARSER_STATIC"] = ""
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        license_file = os.path.join(self.source_folder, self._source_subfolder, "LICENSE")
        if os.path.exists(license_file):
            copy(self, "LICENSE", os.path.dirname(license_file),
                 os.path.join(self.package_folder, "licenses"))
        else:
            # 1.x ships no license file; the BSD terms only live in the banner
            # comment at the top of every source file.
            header = load(
                self,
                os.path.join(
                    self.source_folder, self._source_subfolder, "include", "kdl_parser",
                    "kdl_parser.hpp",
                ),
            )
            banner = header.split("*********************************************************************/")[0]
            save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), banner.strip() + "\n")

        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "kdl_parser")
        self.cpp_info.set_property("cmake_target_name", "kdl_parser::kdl_parser")
        self.cpp_info.libs = ["kdl_parser"]
        self.cpp_info.requires = ["orocos-kdl::orocos-kdl", "urdfdom::urdfdom"]
        if not self._is_ros2:
            self.cpp_info.requires += ["tinyxml::tinyxml", "tinyxml2::tinyxml2"]
        if not self.options.shared:
            self.cpp_info.defines.append("KDL_PARSER_STATIC")
