import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, save


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
    def _source_subfolder(self):
        # The repository holds both kdl_parser and kdl_parser_py; only the C++
        # package is built here.
        return "kdl_parser"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # treeFromXml() streams a TiXmlDocument into a std::stringstream, which
        # TinyXML only declares when it is built with STL support.
        self.options["tinyxml"].with_stl = True

    def requirements(self):
        # All four appear in kdl_parser.hpp: KDL::Tree, urdf::ModelInterface and
        # both TinyXML document types.
        self.requires("orocos-kdl/[>=1.5.2 <2]", transitive_headers=True, transitive_libs=True)
        self.requires("urdfdom/[>=3.1.1 <5]", transitive_headers=True, transitive_libs=True)
        self.requires("tinyxml/2.6.2", transitive_headers=True, transitive_libs=True)
        self.requires("tinyxml2/10.0.0", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 14)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        if not self.options.shared:
            tc.preprocessor_definitions["KDL_PARSER_STATIC"] = ""
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream ships no license file; the BSD terms only live in the banner
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
        self.cpp_info.requires = [
            "orocos-kdl::orocos-kdl",
            "urdfdom::urdfdom",
            "tinyxml::tinyxml",
            "tinyxml2::tinyxml2",
        ]
        if not self.options.shared:
            self.cpp_info.defines.append("KDL_PARSER_STATIC")
