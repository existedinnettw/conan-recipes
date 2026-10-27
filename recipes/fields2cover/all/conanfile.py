import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class Fields2CoverConan(ConanFile):
    name = "fields2cover"
    description = "Coverage path planning library for autonomous agricultural vehicles"
    license = "BSD-3-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/Fields2Cover/Fields2Cover"
    topics = ("coverage-path-planning", "robotics", "agriculture", "geometry")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "parallel": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "parallel": True,
        # Fields2Cover only includes Boost headers (primarily math constants).
        "boost/*:header_only": True,
        "gdal/*:tools": False,
        # GDAL only consumes the PROJ library. Avoid building PROJ's unrelated
        # command-line programs (and keep the dependency graph library-only).
        "proj/*:build_executables": False,
        # Fields2Cover only needs GDAL's geospatial core; Arrow is an optional
        # GDAL format backend with a large unrelated dependency graph.
        "gdal/*:with_arrow": False,
        # OR-Tools brings SoPlex. Its optional Boost support is unrelated to
        # Fields2Cover and otherwise pins a conflicting Boost release.
        "soplex/*:with_boost": False,
        # oneTBB's tbbbind target requires hwloc to be shared.
        "hwloc/*:shared": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # GDAL and Boost types occur in the public Fields2Cover headers. Eigen is
        # included by steering_functions/steering_functions.hpp, also public.
        self.requires("gdal/3.12.1", transitive_headers=True, transitive_libs=True)
        # Keep this aligned with GDAL's GEOS requirement to avoid two versions
        # of GEOS in the same process.
        self.requires("geos/3.12.0", transitive_headers=True, transitive_libs=True)
        self.requires("boost/1.90.0", transitive_headers=True, libs=False)
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("or-tools/9.15", transitive_libs=True)
        self.requires("tinyxml2/11.0.0", transitive_libs=True)
        if self.options.parallel:
            self.requires("onetbb/2022.3.0", transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)
        if self.options.shared and self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} has no dllimport annotations and cannot be built as a DLL")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["fields2cover"], strip_root=True)
        dependency_folder = os.path.join(self.source_folder, ".conan-dependencies")
        for name in ("steering_functions", "matplotplusplus", "nlohmann_json"):
            get(self, **sources[name], strip_root=True, destination=os.path.join(dependency_folder, name))
        matplot_third_party = os.path.join(
            dependency_folder, "matplotplusplus", "source", "3rd_party", "CMakeLists.txt"
        )
        # CImg's optional codec checks use legacy CMake variables. Keep those
        # integrations off: GDAL already owns the image-codec dependencies and
        # Fields2Cover does not need Matplot++ image loading.
        for package in ("JPEG", "TIFF", "PNG"):
            replace_in_file(self, matplot_third_party, f"find_package({package})", f"set({package}_FOUND FALSE)")
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        # Respect Conan's selected language standard (while validate() enforces
        # the upstream minimum) so dependencies use the same feature set.
        replace_in_file(self, cmake_lists, "set(CMAKE_CXX_STANDARD 17)", "# C++ standard supplied by Conan")
        # Boost is part of the public header surface, but upstream currently
        # relies on it being present implicitly instead of declaring it.
        replace_in_file(
            self,
            cmake_lists,
            "find_package(GDAL 3.0 REQUIRED)",
            "find_package(GDAL 3.0 REQUIRED)\nfind_package(Boost REQUIRED)",
        )
        replace_in_file(self, cmake_lists, "    GDAL::GDAL\n", "    GDAL::GDAL\n    Boost::headers\n")
        compiler_options = os.path.join(self.source_folder, "cmake", "F2CCompilerOptions.cmake")
        # Dependency warnings must not make a consumer-selected newer standard
        # fail the package build.
        replace_in_file(
            self,
            compiler_options,
            "-Wall -Wextra -Werror -pedantic",
            "-Wall -Wextra -pedantic",
        )

    def generate(self):
        dependencies = os.path.join(self.source_folder, ".conan-dependencies")
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.cache_variables["ALLOW_PARALLELIZATION"] = bool(self.options.parallel)
        tc.cache_variables["BUILD_TUTORIALS"] = False
        tc.cache_variables["BUILD_PYTHON"] = False
        tc.cache_variables["BUILD_DOC"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        # Upstream's package export omits private FetchContent targets and
        # fails CMake generation for static builds. Conan supplies its own
        # package config, so use upstream's supported no-export path.
        tc.cache_variables["SKBUILD"] = False
        tc.cache_variables["USE_ORTOOLS_RELEASE"] = False
        tc.cache_variables["USE_ORTOOLS_FETCH_SRC"] = False
        tc.cache_variables["USE_ORTOOLS_VENDOR"] = False
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_STEERING_FUNCTIONS"] = os.path.join(
            dependencies, "steering_functions"
        )
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_MATPLOT"] = os.path.join(dependencies, "matplotplusplus")
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_JSON"] = os.path.join(dependencies, "nlohmann_json")
        tc.cache_variables["MATPLOTPP_BUILD_EXAMPLES"] = False
        tc.cache_variables["MATPLOTPP_BUILD_TESTS"] = False
        tc.cache_variables["MATPLOTPP_BUILD_INSTALLER"] = False
        tc.cache_variables["MATPLOTPP_BUILD_PACKAGE"] = False
        tc.cache_variables["MATPLOTPP_BUILD_HIGH_RESOLUTION_WORLD_MAP"] = False
        tc.cache_variables["MATPLOTPP_WITH_OPENCV"] = False
        for package in ("LAPACK", "BLAS", "FFTW", "OpenCV", "Gnuplot"):
            tc.cache_variables[f"CMAKE_DISABLE_FIND_PACKAGE_{package}"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("tinyxml2", "cmake_file_name", "TinyXML2")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE", self.source_folder, licenses)
        dependencies = os.path.join(self.source_folder, ".conan-dependencies")
        copy(self, "LICENSE", os.path.join(dependencies, "steering_functions"),
             os.path.join(licenses, "steering_functions"))
        copy(self, "3rd-party-licenses.txt", os.path.join(dependencies, "steering_functions"),
             os.path.join(licenses, "steering_functions"))
        copy(self, "LICENSE", os.path.join(dependencies, "matplotplusplus"),
             os.path.join(licenses, "matplotplusplus"))
        copy(self, "LICENSE.MIT", os.path.join(dependencies, "nlohmann_json"),
             os.path.join(licenses, "nlohmann_json"))

        CMake(self).install()
        # Upstream installs steering_functions as part of Fields2Cover, but its
        # CMake project omits its public headers. One Fields2Cover public header
        # includes them, so they belong in this package as well.
        copy(self, "*.hpp", os.path.join(dependencies, "steering_functions", "include"),
             os.path.join(self.package_folder, "include"))
        # Matplot++ links this private helper into shared builds. Static builds
        # need the archive beside libmatplot for their final link.
        if not self.options.shared:
            copy(self, "*nodesoup*.a", self.build_folder, os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*nodesoup*.lib", self.build_folder, os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Fields2Cover")
        self.cpp_info.set_property("cmake_target_name", "Fields2Cover::Fields2Cover")
        self.cpp_info.libs = ["Fields2Cover", "steering_functions", "matplot"]
        if not self.options.shared:
            self.cpp_info.libs.append("nodesoup")
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
