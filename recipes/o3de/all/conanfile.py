import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file
from conan.tools.scm import Version
from conan.tools.system import package_manager

# get(excludes=...) needs Conan 2.20.
required_conan_version = ">=2.20"


class O3DEConan(ConanFile):
    name = "o3de"
    license = ("Apache-2.0", "MIT")
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://o3de.org"
    description = ("Core framework libraries of the Open 3D Engine (O3DE): AzCore (AZStd, math, "
                   "reflection and serialization, EBus, components, assets, Lua scripting), "
                   "AzNetworking and AzFramework")
    topics = ("o3de", "game-engine", "azcore", "ebus", "reflection", "serialization", "simulation")
    package_type = "library"
    # Only Code/Framework/{AzCore,AzNetworking,AzFramework} are packaged; the editor,
    # renderer, Gems and assets need O3DE's own build and its prebuilt 3rdParty packages.

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # Linux: AzFramework's native windows and keyboard/mouse input. Without it,
        # AzFramework is built for upstream's "wayland" window manager, which has
        # no native window or input implementation (headless use).
        "with_xcb": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_xcb": True,
        # AzFramework only uses libxkbcommon and libxkbcommon-x11; these would add
        # libxml2 (and libiconv) and the Wayland libraries to the build.
        "xkbcommon/*:xkbregistry": False,
        "xkbcommon/*:with_wayland": False,
    }
    exports_sources = "CMakeLists.txt"

    @property
    def _configuration(self):
        # O3DE's debug, profile and release configurations. Profile (optimized, with
        # tracing, asserts and debug tools) is what O3DE develops with; release strips them.
        return {
            "Debug": "debug",
            "RelWithDebInfo": "profile",
            "Release": "profile",
            "MinSizeRel": "release",
        }[str(self.settings.build_type)]

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        if self.settings.os != "Linux":
            self.options.rm_safe("with_xcb")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Upstream's Lua 5.4.4, RapidJSON and cityhash packages are unmodified.
        self.requires("lua/5.4.4", transitive_headers=True)
        self.requires("rapidjson/cci.20230929", transitive_headers=True)
        self.requires("zlib/[>=1.2.11 <2]", transitive_headers=True)
        self.requires("zstd/[>=1.5 <1.6]", transitive_headers=True)
        self.requires("lz4/1.10.0", transitive_headers=True)
        self.requires("cityhash/cci.20130801")
        self.requires("openssl/[>=3 <4]")
        self.requires("libunwind/1.8.1")
        if self.options.get_safe("with_xcb"):
            # The Xcb headers AzFramework installs include xcb and xkbcommon headers.
            self.requires("xorg/system", transitive_headers=True)
            self.requires("xkbcommon/1.13.1", transitive_headers=True)

    def system_requirements(self):
        # xcb-xinput is not among xorg/system's packages.
        if self.options.get_safe("with_xcb"):
            package_manager.Apt(self).install(["libxcb-xinput-dev"], update=True, check=True)
            package_manager.Yum(self).install(["libxcb-devel"], update=True, check=True)
            package_manager.Dnf(self).install(["libxcb-devel"], update=True, check=True)
            package_manager.PacMan(self).install(["libxcb"], update=True, check=True)
            package_manager.Zypper(self).install(["libxcb-devel"], update=True, check=True)

    def validate(self):
        check_min_cppstd(self, 20)
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux")
        if self.settings.compiler not in ("gcc", "clang"):
            raise ConanInvalidConfiguration(f"{self.ref} requires GCC or Clang")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        # Only Code/Framework and cmake/AzAutoGen.py are used; the rest (Gems, assets,
        # tools) is most of the archive.
        get(self, **sources["o3de"], strip_root=True, destination="o3de",
            excludes=["*/Gems/*", "*/Assets/*", "*/AutomatedTesting/*", "*/Templates/*",
                      "*/Tools/*", "*/Docker/*", "*/scripts/*", "*/python/*", "*/Registry/*",
                      "*/Code/Editor/*", "*/Code/Legacy/*", "*/Code/LauncherUnified/*",
                      "*/Code/Framework/AzToolsFramework/*", "*/Code/Framework/AzQtComponents/*",
                      "*/Code/Framework/AtomCore/*", "*/Code/Framework/AzManipulatorTestFramework/*"])
        get(self, **sources["rapidxml"], destination="rapidxml")
        get(self, **sources["jinja2"], strip_root=True, destination=os.path.join("python", "jinja2"))
        get(self, **sources["markupsafe"], strip_root=True, destination=os.path.join("python", "markupsafe"))
        copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["O3DE_CONFIGURATION"] = self._configuration
        tc.cache_variables["O3DE_WITH_XCB"] = bool(self.options.get_safe("with_xcb"))
        # MarkupSafe falls back to pure Python when its C speedups are not built.
        tc.cache_variables["O3DE_PYTHONPATH"] = os.pathsep.join(
            os.path.join(self.source_folder, "python", p, "src") for p in ("jinja2", "markupsafe"))
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        if not self.options.get_safe("with_xcb", True):
            # Upstream's "wayland" window manager stops at #error before its "return nullptr";
            # AzFramework handles a missing application/window/input implementation.
            replace_in_file(self, os.path.join(self.source_folder, "o3de", "Code", "Framework", "AzFramework",
                                               "Platform", "Linux", "AzFramework", "Components",
                                               "NativeUISystemComponent_Linux.cpp"),
                            '#error "Linux Window Manager Wayland not supported."',
                            "// headless: no implementation")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        o3de = os.path.join(self.source_folder, "o3de")
        copy(self, "LICENSE*", o3de, os.path.join(self.package_folder, "licenses"))
        copy(self, "license.txt", os.path.join(self.source_folder, "rapidxml", "RapidXML", "include", "rapidxml"),
             os.path.join(self.package_folder, "licenses", "rapidxml"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream has no CMake package for these libraries; the targets are named like
        # O3DE's own (AZ::AzCore, ...), and headers are included as <AzCore/...>.
        self.cpp_info.set_property("cmake_file_name", "o3de")
        # See the install rules in CMakeLists.txt.
        includedirs = [os.path.join("include", "O3DE"),
                       os.path.join("include", "O3DE", "Platform", "Linux"),
                       os.path.join("include", "O3DE", "Platform", "Common")]

        config = {
            "debug": ["_DEBUG", "AZ_DEBUG_BUILD", "AZ_ENABLE_TRACING", "AZ_ENABLE_DEBUG_TOOLS"],
            "profile": ["_PROFILE", "AZ_PROFILE_BUILD", "NDEBUG", "AZ_ENABLE_TRACING", "AZ_ENABLE_DEBUG_TOOLS"],
            "release": ["_RELEASE", "RELEASE", "AZ_RELEASE_BUILD", "NDEBUG"],
        }[self._configuration]
        defines = ["LINUX", "LINUX64"] + config
        if not self.options.shared:
            defines.append("AZ_MONOLITHIC_BUILD")
        # See CMakeLists.txt.
        if self.settings.compiler == "gcc" or \
                (self.settings.compiler == "clang" and Version(self.settings.compiler.version) < "19"):
            defines.append("O3DE_DISABLE_CONDITIONAL_EXPLICIT=1")
        cxxflags = ["-msse4.1"] if self.settings.arch == "x86_64" else []

        azcore = self.cpp_info.components["azcore"]
        azcore.set_property("cmake_target_name", "AZ::AzCore")
        azcore.libs = ["AzCore"]
        azcore.includedirs = includedirs
        azcore.defines = defines
        azcore.cxxflags = cxxflags
        azcore.system_libs = ["pthread", "dl", "atomic"]
        azcore.requires = ["lua::lua", "rapidjson::rapidjson", "zlib::zlib", "zstd::zstd",
                           "cityhash::cityhash", "libunwind::libunwind"]

        aznetworking = self.cpp_info.components["aznetworking"]
        aznetworking.set_property("cmake_target_name", "AZ::AzNetworking")
        aznetworking.libs = ["AzNetworking"]
        aznetworking.includedirs = includedirs
        aznetworking.requires = ["azcore", "rapidjson::rapidjson", "zstd::zstd", "openssl::openssl"]

        azframework = self.cpp_info.components["azframework"]
        azframework.set_property("cmake_target_name", "AZ::AzFramework")
        azframework.libs = ["AzFramework"]
        azframework.includedirs = includedirs
        azframework.requires = ["azcore", "aznetworking", "zstd::zstd", "lz4::lz4"]
        if self.options.get_safe("with_xcb"):
            azframework.defines = ["PAL_TRAIT_LINUX_WINDOW_MANAGER_XCB"]
            azframework.includedirs = includedirs + [os.path.join("include", "O3DE", "Platform", "Common", "Xcb")]
            azframework.requires += ["xorg::xcb", "xorg::xcb-xkb", "xorg::xcb-xfixes", "xorg::xcb-randr",
                                     "xorg::xcb-keysyms", "xkbcommon::libxkbcommon",
                                     "xkbcommon::libxkbcommon-x11"]
            azframework.system_libs = ["xcb-xinput"]
        else:
            azframework.defines = ["PAL_TRAIT_LINUX_WINDOW_MANAGER_WAYLAND"]

        nativeui = self.cpp_info.components["azframework-nativeui"]
        nativeui.set_property("cmake_target_name", "AZ::AzFramework.NativeUI")
        nativeui.libs = ["AzFramework.NativeUI"]
        nativeui.includedirs = includedirs
        nativeui.requires = ["azframework"]
