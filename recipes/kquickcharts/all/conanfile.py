import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir
from conan.tools.scm import Version


class KQuickChartsConan(ConanFile):
    name = "kquickcharts"
    description = "KDE's QtQuick module providing high-performance charts"
    license = ("LGPL-2.1-only", "LGPL-3.0-only", "BSD-2-Clause", "MIT", "CC0-1.0")
    url = "https://invent.kde.org/frameworks/kquickcharts"
    homepage = "https://api.kde.org/kquickcharts-index.html"
    topics = ("kde", "kde-frameworks", "qt", "qml", "qtquick", "charts")
    # Both QML modules are runtime-loaded plugins backed by shared libraries.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"
    # Same Qt options as the kirigami recipe, so one Qt binary serves both.
    default_options = {
        "qt/*:shared": True,
        "qt/*:gui": True,
        "qt/*:qtdeclarative": True,
        "qt/*:qtshadertools": True,
        "qt/*:qtsvg": True,
        "qt/*:qttools": True,
        "qt/*:with_dbus": True,
        "qt/*:with_pq": False,
    }

    @property
    def _qt_min_version(self):
        return "6.9.0"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("qt/6.11.1", transitive_headers=True, transitive_libs=True, run=True)

    def build_requirements(self):
        self.tool_requires("extra-cmake-modules/6.30.0")
        # kquickcharts and ECM require CMake 3.29.
        self.tool_requires("cmake/[>=3.29 <5]")

    def validate(self):
        check_min_cppstd(self, 20)
        qt = self.dependencies["qt"]
        if Version(qt.ref.version) < self._qt_min_version:
            raise ConanInvalidConfiguration(f"{self.ref} requires qt >= {self._qt_min_version}")
        if not qt.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} loads its QML plugins at runtime and needs qt/*:shared=True")
        missing = [opt for opt in ("gui", "qtdeclarative", "qtshadertools") if not qt.options.get_safe(opt)]
        if missing:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires " + ", ".join(f"qt/*:{opt}=True" for opt in missing))

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = True
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_QCH"] = False
        # ecm_generate_qdoc() builds the API documentation when it finds Qt6Tools as a
        # separate package, which would be a system Qt rather than Conan's.
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6Tools"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6ToolsTools"] = True
        tc.generate()

    def _patch_sources(self):
        # Installing a git pre-commit hook touches the source folder.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "kde_configure_git_pre_commit_hook(CHECKS CLANG_FORMAT)", "")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "*", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # package_info() models the targets; upstream's config file looks Qt up as the
        # Qt6Core package, which Conan's Qt does not provide.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "KF6QuickCharts")

        # Neither library installs headers: charts are used from QML.
        charts = self.cpp_info.components["quickcharts"]
        charts.set_property("cmake_target_name", "KF6::QuickCharts")
        charts.libs = ["QuickCharts"]
        charts.includedirs = []
        charts.requires = ["qt::qtCore", "qt::qtGui", "qt::qtQml", "qt::qtQuick"]

        controls = self.cpp_info.components["quickchartscontrols"]
        controls.set_property("cmake_target_name", "KF6::QuickChartsControls")
        controls.libs = ["QuickChartsControls"]
        controls.includedirs = []
        controls.requires = ["quickcharts", "qt::qtCore", "qt::qtGui", "qt::qtQml", "qt::qtQuick",
                             "qt::qtQuickControls2"]

        # QQmlEngine finds `import org.kde.quickcharts` through QML_IMPORT_PATH.
        qml_dir = os.path.join(self.package_folder, "lib", "qml")
        self.runenv_info.prepend_path("QML_IMPORT_PATH", qml_dir)
        self.buildenv_info.prepend_path("QML_IMPORT_PATH", qml_dir)
