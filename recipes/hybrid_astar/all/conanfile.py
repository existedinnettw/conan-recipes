import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class HybridAstarConan(ConanFile):
    name = "hybrid_astar"
    license = "BSD-3-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/karlkurzer/path_planner"
    description = (
        "Hybrid A* path planner for nonholonomic vehicles (karlkurzer/path_planner): the search, "
        "collision checking and Voronoi-based smoothing, without the ROS node"
    )
    topics = ("path-planning", "hybrid-astar", "motion-planning", "robotics", "autonomous-driving")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {
        "shared": False,
        "fPIC": True,
        # Conan Center's ompl only builds as a shared library with GCC and Clang.
        "ompl/*:shared": True,
        # Conan Center's boost 1.90 builds boost_cobalt_io_ssl with GCC 14, then rejects it
        # in package_info; nothing here uses Cobalt.
        "boost/*:without_cobalt": True,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # algorithm.h includes the OMPL state spaces; boost::heap is only used in algorithm.cpp.
        self.requires("ompl/1.7.0", transitive_headers=True)
        self.requires("boost/1.90.0", libs=False)

    def validate(self):
        # OMPL 1.7 needs C++17.
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "hybrid_astar")
        self.cpp_info.set_property("cmake_target_name", "hybrid_astar::hybrid_astar")
        self.cpp_info.libs = ["hybrid_astar"]
        self.cpp_info.requires = ["ompl::ompl", "boost::headers"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
