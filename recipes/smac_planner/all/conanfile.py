import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save


class SmacPlannerConan(ConanFile):
    name = "smac_planner"
    license = ("Apache-2.0", "BSD-3-Clause", "MIT")
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/rapyuta-robotics/smac_planner"
    description = (
        "Smac planner (rapyuta-robotics' ROS 1 port of Nav2's): A*, Hybrid-A* and State Lattice "
        "search, collision checking and path smoothing on a 2D costmap, without the ROS plugin"
    )
    topics = ("path-planning", "hybrid-astar", "state-lattice", "motion-planning", "robotics", "navigation")
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
        copy(self, "ros_compat/*", self.recipe_folder, self.export_sources_folder)
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
        # The public headers include OMPL state spaces, nlohmann/json, and costmap_2d.h
        # (boost::recursive_mutex).
        self.requires("ompl/1.7.0", transitive_headers=True)
        self.requires("boost/1.90.0", transitive_headers=True, transitive_libs=True)
        self.requires("nlohmann_json/3.12.0", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 17)
        # The nodes keep their motion tables and heuristics in static data members, which
        # WINDOWS_EXPORT_ALL_SYMBOLS does not make importable from a DLL.
        if self.options.shared and self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} has no dllimport annotations and cannot be built as a DLL")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["smac_planner"], strip_root=True)
        get(self, **sources["navigation"], strip_root=True, destination="navigation")
        apply_conandata_patches(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE", self.source_folder, licenses)
        # The bundled robin_hood.h (MIT) and ROS navigation (BSD-3-Clause) have no license
        # files; their terms head the sources.
        robin_hood = load(self, os.path.join(self.source_folder, "include", "smac_planner", "thirdparty", "robin_hood.h"))
        save(self, os.path.join(licenses, "robin_hood-LICENSE"),
             robin_hood[:robin_hood.index("#ifndef SMAC_PLANNER__THIRDPARTY__ROBIN_HOOD_H_")])
        navigation = load(self, os.path.join(self.source_folder, "navigation", "costmap_2d", "src", "costmap_2d.cpp"))
        save(self, os.path.join(licenses, "navigation-LICENSE"), navigation[:navigation.index("*/") + 2] + "\n")
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "smac_planner")
        self.cpp_info.set_property("cmake_target_name", "smac_planner::smac_planner")
        self.cpp_info.libs = ["smac_planner"]
        # ros_compat holds the ROS header shims and the ROS navigation headers that the
        # public headers include by their ROS paths.
        self.cpp_info.includedirs = ["include", os.path.join("include", "smac_planner", "ros_compat")]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.requires = [
            "ompl::ompl",
            "boost::headers",
            "boost::thread",
            "nlohmann_json::nlohmann_json",
        ]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
