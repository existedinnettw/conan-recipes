import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ExtraCmakeModulesConan(ConanFile):
    name = "extra-cmake-modules"
    description = "KDE's extra CMake modules (ECM), needed to build KDE Frameworks"
    license = ("BSD-3-Clause", "BSD-2-Clause", "MIT")
    url = "https://invent.kde.org/frameworks/extra-cmake-modules"
    homepage = "https://api.kde.org/ecm/"
    topics = ("cmake", "cmake-modules", "kde", "kde-frameworks", "build-settings")
    package_type = "build-scripts"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def build_requirements(self):
        # ECM and the KDE Frameworks built with it require CMake 3.29.
        self.tool_requires("cmake/[>=3.29 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_HTML_DOCS"] = False
        tc.cache_variables["BUILD_QTHELP_DOCS"] = False
        tc.cache_variables["BUILD_MAN_DOCS"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        # Everything lands in <package>/share/ECM; ECMConfig.cmake locates the modules
        # relative to itself, so the package is relocatable.
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "*", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # Consumers use upstream's own ECMConfig.cmake: find_package(ECM NO_MODULE).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("share", "ECM", "cmake")]
