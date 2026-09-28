import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file
from conan.tools.scm import Version


class QuickGraphLibConan(ConanFile):
    name = "quickgraphlib"
    description = "A scientific graphing library for QtQuick"
    license = "MIT"
    url = "https://github.com/refeyn/QuickGraphLib"
    homepage = "https://refeyn.github.io/QuickGraphLib"
    topics = ("qt", "qml", "qtquick", "graph", "plot", "charts", "scientific")
    # The QuickGraphLib, QuickGraphLib.GraphItems and QuickGraphLib.PreFabs QML modules
    # are runtime-loaded plugins; nothing is linked or included by consumers.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"
    # Same Qt options as the kirigami and kquickcharts recipes, so one Qt binary
    # serves all of them.
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
        # qt_standard_project_setup(REQUIRES 6.10)
        return "6.10.0"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Its consumers are Qt Quick applications, which build against this Qt.
        self.requires("qt/6.11.1", transitive_headers=True, transitive_libs=True, run=True)

    def validate(self):
        check_min_cppstd(self, 17)
        qt = self.dependencies["qt"]
        if Version(qt.ref.version) < self._qt_min_version:
            raise ConanInvalidConfiguration(f"{self.ref} requires qt >= {self._qt_min_version}")
        if not qt.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} loads its QML plugins at runtime and needs qt/*:shared=True")
        missing = [opt for opt in ("gui", "qtdeclarative", "qtshadertools", "qtsvg")
                   if not qt.options.get_safe(opt)]
        if missing:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires " + ", ".join(f"qt/*:{opt}=True" for opt in missing))

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # The PySide6 bindings and their .pyi stubs are for the PyPI package.
        tc.cache_variables["ENABLE_PYTHON"] = False
        tc.cache_variables["ENABLE_STUB_GENERATION"] = False
        tc.cache_variables["INSTALL_SUBPATH"] = "lib/qml"
        # The QuickGraphLib plugin links libQuickGraphLib, installed next to it.
        if is_apple_os(self):
            tc.cache_variables["CMAKE_INSTALL_RPATH"] = "@loader_path"
        elif self.settings.os != "Windows":
            tc.cache_variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.generate()

    def _patch_sources(self):
        # Upstream forces a universal macOS build, overriding the architecture Conan
        # asks for.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        'set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "" FORCE)', "")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENCE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # QML only: upstream installs no headers and no CMake config.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.requires = ["qt::qtCore", "qt::qtGui", "qt::qtQml", "qt::qtQuick", "qt::qtSvg"]

        # QQmlEngine finds `import QuickGraphLib` through QML_IMPORT_PATH.
        qml_dir = os.path.join(self.package_folder, "lib", "qml")
        self.runenv_info.prepend_path("QML_IMPORT_PATH", qml_dir)
        self.buildenv_info.prepend_path("QML_IMPORT_PATH", qml_dir)
