import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir
from conan.tools.scm import Version


class KirigamiConan(ConanFile):
    name = "kirigami"
    description = "KDE's QtQuick based components set for building convergent user interfaces"
    license = ("LGPL-2.0-or-later", "LGPL-2.1-or-later", "LGPL-3.0-or-later", "GPL-2.0-or-later",
               "MIT", "BSD-2-Clause", "CC0-1.0")
    url = "https://invent.kde.org/frameworks/kirigami"
    homepage = "https://develop.kde.org/frameworks/kirigami/"
    topics = ("kde", "kde-frameworks", "qt", "qml", "qtquick", "ui", "convergent")
    # Every QML module is a shared plugin backed by a shared library; upstream's static
    # build (for Android and iOS) links all of them into the consumer and needs a static Qt.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_dbus": [True, False],
        "with_translations": [True, False],
    }
    default_options = {
        "with_dbus": True,
        "with_translations": True,
        "qt/*:shared": True,
        "qt/*:gui": True,
        "qt/*:qtdeclarative": True,
        "qt/*:qtshadertools": True,
        "qt/*:qtsvg": True,
        "qt/*:qttools": True,
        "qt/*:with_dbus": True,
        # Kirigami needs no SQL driver, and Qt's PostgreSQL plugin fails to link
        # against the static libpq (missing pgcommon/pgport symbols).
        "qt/*:with_pq": False,
    }

    @property
    def _qt_min_version(self):
        return "6.9.0"

    def config_options(self):
        # Upstream only uses DBus (portal settings, tablet mode) on Linux and the BSDs.
        if self.settings.os not in ("Linux", "FreeBSD"):
            del self.options.with_dbus

    def configure(self):
        if not self.options.with_translations:
            self.options["qt"].qttools = False
        if not self.options.get_safe("with_dbus"):
            self.options["qt"].with_dbus = False

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Kirigami's public headers include QtQuick's, and its QML plugins need the
        # Qt Quick Controls, Svg and ShaderTools runtime.
        self.requires("qt/6.11.1", transitive_headers=True, transitive_libs=True, run=True)

    def build_requirements(self):
        self.tool_requires("extra-cmake-modules/6.30.0")
        # Kirigami and ECM require CMake 3.29.
        self.tool_requires("cmake/[>=3.29 <5]")

    def validate(self):
        check_min_cppstd(self, 20)
        qt = self.dependencies["qt"]
        if Version(qt.ref.version) < self._qt_min_version:
            raise ConanInvalidConfiguration(f"{self.ref} requires qt >= {self._qt_min_version}")
        if not qt.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} loads its QML plugins at runtime and needs qt/*:shared=True")
        required = ["gui", "qtdeclarative", "qtshadertools", "qtsvg"]
        if self.options.with_translations:
            required.append("qttools")
        if self.options.get_safe("with_dbus"):
            required.append("with_dbus")
        missing = [opt for opt in required if not qt.options.get_safe(opt)]
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
        tc.cache_variables["USE_DBUS"] = bool(self.options.get_safe("with_dbus"))
        tc.cache_variables["KF_SKIP_PO_PROCESSING"] = not self.options.with_translations
        # OpenMP only speeds up Kirigami.ImageColors, and would add the compiler's OpenMP
        # runtime as a hidden dependency.
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = True
        # ecm_generate_qdoc() builds the API documentation when it finds Qt6Tools as a
        # separate package, which would be a system Qt rather than Conan's.
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6Tools"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Qt6ToolsTools"] = True
        tc.generate()

    def _patch_sources(self):
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        # Conan's Qt comes as a single Qt6 package. Its build modules already define
        # Qt6::GuiPrivate, which upstream looks up as a separate package from Qt 6.10 on.
        replace_in_file(self, cmakelists,
                        "find_package(Qt6GuiPrivate ${REQUIRED_QT_VERSION} REQUIRED NO_MODULE)",
                        "")
        replace_in_file(self, cmakelists,
                        "find_package(Qt6DBus ${REQUIRED_QT_VERSION} REQUIRED NO_MODULE)",
                        "find_package(Qt6 ${REQUIRED_QT_VERSION} REQUIRED NO_MODULE COMPONENTS DBus)")
        # Installing a git pre-commit hook and writing .qmllint.ini are developer
        # conveniences that touch the source folder.
        replace_in_file(self, cmakelists,
                        "configure_file(qmllint.ini.in ${CMAKE_SOURCE_DIR}/.qmllint.ini)", "")
        replace_in_file(self, cmakelists,
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
        # package_info() models the targets; upstream's config files look Qt up as
        # Qt6Core, Qt6Qml, ... packages, which Conan's Qt does not provide.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "KF6Kirigami")

        def _qt(*modules):
            return [f"qt::qt{m}" for m in modules]

        platform = self.cpp_info.components["platform"]
        platform.set_property("cmake_target_name", "KF6::KirigamiPlatform")
        platform.libs = ["KirigamiPlatform"]
        platform.includedirs = [os.path.join("include", "KF6"),
                                os.path.join("include", "KF6", "Kirigami", "Platform")]
        platform.requires = _qt("Core", "Gui", "Qml", "Quick", "QuickControls2")
        if self.options.get_safe("with_dbus"):
            platform.requires += _qt("DBus")

        # The libraries behind the org.kde.kirigami.* QML modules. They have no public
        # headers; libKirigami links to them, so a linker has to find them too.
        backing = ["Controls", "Delegates", "Dialogs", "Forms", "FormsPrivateCards",
                   "FormsPrivateFlat", "FormsPrivateTemplates", "Layouts", "LayoutsPrivate",
                   "Polyfill", "Primitives", "Private", "Templates"]
        for name in backing:
            component = self.cpp_info.components[f"kirigami_{name.lower()}"]
            component.libs = [f"Kirigami{name}"]
            component.includedirs = []
            component.requires = ["platform"] + _qt("Core", "Gui", "Qml", "Quick", "QuickControls2")

        kirigami = self.cpp_info.components["kirigami"]
        kirigami.set_property("cmake_target_name", "KF6::Kirigami")
        kirigami.set_property("cmake_target_aliases", ["KF6::Kirigami2"])
        kirigami.libs = ["Kirigami"]
        kirigami.includedirs = []
        kirigami.requires = (["platform"] + [f"kirigami_{name.lower()}" for name in backing]
                             + _qt("Core", "Gui", "Qml", "Quick", "Concurrent"))

        # QQmlEngine finds `import org.kde.kirigami` through QML_IMPORT_PATH.
        qml_dir = os.path.join(self.package_folder, "lib", "qml")
        self.runenv_info.prepend_path("QML_IMPORT_PATH", qml_dir)
        self.buildenv_info.prepend_path("QML_IMPORT_PATH", qml_dir)
