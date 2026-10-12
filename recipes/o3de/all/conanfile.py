import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.scm import Version
from conan.tools.system import package_manager

# get(excludes=...) needs Conan 2.20.
required_conan_version = ">=2.20"


class O3DEConan(ConanFile):
    name = "o3de"
    license = ("Apache-2.0", "MIT")
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://o3de.org"
    description = ("Libraries of the Open 3D Engine (O3DE): the core framework (AzCore, AzNetworking, "
                   "AzFramework), the Atom renderer, the editor framework (AzQtComponents, "
                   "AzToolsFramework) and the engine's Gems")
    topics = ("o3de", "game-engine", "azcore", "ebus", "reflection", "serialization", "simulation",
              "renderer", "atom", "gems")
    package_type = "library"
    # Only libraries are packaged: no Editor, AssetProcessor or other executables, no assets.
    # Libraries that need a 3rdParty package upstream ships prebuilt and neither Conan Center nor
    # this repository has (PhysX 5, NvCloth, squish-ccr, ISPCTexComp, ...) are left out, as are the
    # ones that embed Python (EditorPythonBindings, AtomToolsFramework, and EditorLib, which uses
    # it). The shader builder (the AtomShader Gem, with_editor) uses this repository's mcpp, azslc
    # and directx-shader-compiler recipes.

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # Linux: AzFramework's native windows and keyboard/mouse input. Without it,
        # AzFramework is built for upstream's "wayland" window manager, which has
        # no native window or input implementation (headless use).
        "with_xcb": [True, False],
        # AzQtComponents, AzToolsFramework, and the Gems' editor and builder libraries (Qt 5).
        "with_editor": [True, False],
        # Comma-separated Gems to build; the Gems they depend on (gem.json) are added.
        "gems": ["ANY"],
        # AssetProcessor, AssetProcessorBatch and AssetBuilder: the package becomes an engine root
        # (engine.json, Registry, Assets and the Gems' data) they process projects' assets with.
        "with_asset_processor": [True, False],
        # The generic game launcher (O3DE.GameLauncher --project-path=<project>), which runs a project
        # from its processed assets; the package becomes an engine root as with with_asset_processor.
        "with_launcher": [True, False],
    }
    # Atom's runtime (RHI with its Vulkan and Null backends, RPI, the common render features and
    # their components, ImGui rendering), and the Gems a default O3DE project uses at runtime that
    # need nothing missing from Conan. Profiler, AudioSystem and AtomImGuiTools are used by Atom_Utils,
    # LmbrCentral and CommonFeaturesAtom, but are not in their gem.json.
    _default_gems = (
        "Atom_RHI", "Atom_RPI", "Atom_Bootstrap", "Atom_Feature_Common", "Atom_Component_DebugCamera",
        "CommonFeaturesAtom", "AtomImGuiTools", "ImGui", "Profiler", "LmbrCentral", "AudioSystem",
        "CameraFramework", "Camera", "DebugDraw", "GameState", "SaveData", "ScriptEvents", "RemoteTools",
    )
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_xcb": True,
        "with_editor": False,
        "gems": ",".join(_default_gems),
        "with_asset_processor": False,
        "with_launcher": False,
        # AzFramework only uses libxkbcommon and libxkbcommon-x11; these would add
        # libxml2 (and libiconv) and the Wayland libraries to the build.
        "xkbcommon/*:xkbregistry": False,
        "xkbcommon/*:with_wayland": False,
        # Only the Core, Gui, Widgets, Svg, Xml, Network, Concurrent, OpenGL and Test modules are used.
        "qt/*:shared": True,
        "qt/*:qtsvg": True,
        "qt/*:with_sqlite3": False,
        "qt/*:with_mysql": False,
        "qt/*:with_pq": False,
        "qt/*:with_odbc": False,
        "qt/*:with_openal": False,
        "qt/*:with_icu": False,
    }
    exports_sources = "CMakeLists.txt", "o3de_compat.cmake"

    def export_sources(self):
        export_conandata_patches(self)

    @property
    def _gems(self):
        return [g.strip() for g in str(self.options.gems).split(",") if g.strip()]

    @property
    def _with_shader_builder(self):
        # The AtomShader Gem's libraries only exist with the editor; the Atom Gem depends on it.
        return self.options.with_editor and ("AtomShader" in self._gems or "Atom" in self._gems)

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
        # 3rdParty packages of the Gems. Which of them the build uses depends on the Gems' dependency
        # closure (gem.json), which is only known at build time: unused ones are ignored in
        # package_info().
        if self._gems:
            # Atom_Feature_Common, Atom_Utils, AtomFont
            self.requires("libtiff/[>=4.6 <5]")
            self.requires("libpng/[>=1.6 <2]")
            self.requires("freetype/[>=2.13 <3]")
        if self.options.with_editor:
            # Public headers of AzQtComponents and AzToolsFramework include Qt's.
            self.requires("qt/5.15.19", transitive_headers=True, transitive_libs=True)
            self.requires("sqlite3/[>=3.45 <4]")
            # Atom_RPI's builders
            if self._gems:
                self.requires("meshoptimizer/0.25")
            # AssetBuilderSDK
            self.requires("xxhash/[>=0.8.1 <0.9]")
            if self._with_shader_builder:
                self.requires("mcpp/2.7.2-o3de")
                # Run by the shader builder, which looks for them under the running executable's
                # Builders/AZSLc and Builders/DirectXShaderCompiler/bin folders (or an azslc path
                # set in the settings registry).
                self.requires("azslc/1.8.22", headers=False, libs=False, run=True)
                self.requires("directx-shader-compiler/1.8.2505.1-o3de", headers=False, libs=False, run=True)
        if self.options.with_launcher:
            # CrySystem
            self.requires("expat/[>=2.6 <3]")
        if self.options.get_safe("with_xcb"):
            # The Xcb headers AzFramework installs include xcb and xkbcommon headers.
            self.requires("xorg/system", transitive_headers=True)
            # force: qt/5.15.x (with_editor) pins xkbcommon/1.5.0.
            self.requires("xkbcommon/1.13.1", transitive_headers=True, force=True)

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
        if (self._gems or self.options.with_editor) and self.settings.compiler != "clang":
            # Upstream builds Linux with Clang only. The core framework builds with GCC too, but the
            # Gems and the editor libraries use Clang-only C++ (class-scope explicit specializations,
            # anonymous structs with non-trivial members, ...).
            raise ConanInvalidConfiguration(f"{self.ref} needs Clang for Gems and with_editor; "
                                            f"use -o {self.name}/*:gems= for the core framework with GCC")
        if self.options.with_asset_processor and not (self.options.with_editor and self.options.shared):
            # AssetProcessor loads the Gems' builders as modules (upstream builds tools shared only).
            raise ConanInvalidConfiguration(f"{self.ref} with_asset_processor needs with_editor=True and shared=True")
        if self.options.with_launcher and not self.options.shared:
            # The generic launcher loads the Gems' modules (upstream builds it for shared builds only).
            raise ConanInvalidConfiguration(f"{self.ref} with_launcher needs shared=True")
        if self.options.with_editor and not self.dependencies["qt"].options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} with_editor needs qt/*:shared=True")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        # The sample projects and Gems, templates, Python and scripts are not used. The assets stay:
        # libraries' file lists include asset file lists, and the editor libraries' Qt resources
        # embed the editor icons. Patterns are anchored at the archive's root folder.
        unused = ["AutomatedTesting", "Templates", "Docker", "scripts", "python", "Gems/AtomContent",
                  "Gems/LyShineExamples", "Gems/ScriptCanvasTesting"]
        get(self, **sources["o3de"], strip_root=True, destination="o3de",
            excludes=[f"o3de-{self.version}/{d}/*" for d in unused])
        get(self, **sources["rapidxml"], destination="rapidxml")
        get(self, **sources["jinja2"], strip_root=True, destination=os.path.join("python", "jinja2"))
        get(self, **sources["markupsafe"], strip_root=True, destination=os.path.join("python", "markupsafe"))
        for f in ("CMakeLists.txt", "o3de_compat.cmake"):
            copy(self, f, self.export_sources_folder, self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["O3DE_CONFIGURATION"] = self._configuration
        tc.cache_variables["O3DE_WITH_XCB"] = bool(self.options.get_safe("with_xcb"))
        tc.cache_variables["O3DE_WITH_EDITOR"] = bool(self.options.with_editor)
        tc.cache_variables["O3DE_GEMS"] = ";".join(self._gems)
        tc.cache_variables["O3DE_WITH_ASSET_PROCESSOR"] = bool(self.options.with_asset_processor)
        tc.cache_variables["O3DE_WITH_LAUNCHER"] = bool(self.options.with_launcher)
        # MarkupSafe falls back to pure Python when its C speedups are not built.
        tc.cache_variables["O3DE_PYTHONPATH"] = os.pathsep.join(
            os.path.join(self.source_folder, "python", p, "src") for p in ("jinja2", "markupsafe"))
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        apply_conandata_patches(self)
        if not self.options.get_safe("with_xcb", True):
            # Upstream's "wayland" window manager stops at #error before its "return nullptr";
            # AzFramework handles a missing application/window/input implementation.
            replace_in_file(self, os.path.join(self.source_folder, "o3de", "Code", "Framework", "AzFramework",
                                               "Platform", "Linux", "AzFramework", "Components",
                                               "NativeUISystemComponent_Linux.cpp"),
                            '#error "Linux Window Manager Wayland not supported."',
                            "// headless: no implementation")

        if self.options.with_editor:
            # LmbrCentral's translation builder runs Qt's lrelease from the executables' folder; the
            # step that copies it there and fixes its RPATH (an output no target needs, so never run).
            replace_in_file(self, os.path.join(self.source_folder, "o3de", "Gems", "LmbrCentral", "Code", "Platform",
                                               "Linux", "lrelease_linux.cmake"),
                            "add_custom_command(TARGET LmbrCentral.Editor POST_BUILD",
                            "add_custom_command(OUTPUT lrelease-unused")

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
        if self.options.with_asset_processor and self._with_shader_builder:
            # Where the shader builder runs them from (relative to the executables)
            builders = os.path.join(self.package_folder, "bin", "Builders")
            azslc = self.dependencies["azslc"].cpp_info
            copy(self, "azslc", azslc.bindir, os.path.join(builders, "AZSLc"))
            dxc = self.dependencies["directx-shader-compiler"].cpp_info
            copy(self, "dx*", dxc.bindir, os.path.join(builders, "DirectXShaderCompiler", "bin"))
            copy(self, "libdxcompiler.so*", dxc.libdir, os.path.join(builders, "DirectXShaderCompiler", "lib"))

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
        else:
            azframework.defines = ["PAL_TRAIT_LINUX_WINDOW_MANAGER_WAYLAND"]

        nativeui = self.cpp_info.components["azframework-nativeui"]
        nativeui.set_property("cmake_target_name", "AZ::AzFramework.NativeUI")
        nativeui.libs = ["AzFramework.NativeUI"]
        nativeui.includedirs = includedirs
        nativeui.requires = ["azframework"]
        if self.options.get_safe("with_xcb"):
            # The native windows and input (see CMakeLists.txt)
            nativeui.includedirs = includedirs + [os.path.join("include", "O3DE", "Platform", "Common", "Xcb")]
            nativeui.requires += ["xorg::xcb", "xorg::xcb-xkb", "xorg::xcb-xfixes", "xorg::xcb-randr",
                                  "xorg::xcb-keysyms", "xkbcommon::libxkbcommon", "xkbcommon::libxkbcommon-x11"]
            nativeui.system_libs = ["xcb-xinput"]

        # The other libraries, as described by the build (see o3de_compat.cmake's o3de_finalize).
        # Component names are the CMake target names with "::" as "_", e.g. Gem_Atom_RPI.Public
        # for Gem::Atom_RPI.Public.
        with open(os.path.join(self.package_folder, "res", "o3de-components.json")) as f:
            manifest = json.load(f)
        for name, info in manifest.items():
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", info["target"])
            # A Gem module of a shared build is loaded at runtime (AZ::ModuleManager), not linked.
            if "lib" in info and info["type"] != "MODULE_LIBRARY":
                component.libs = [info["lib"]]
            component.includedirs = info["includedirs"] + includedirs
            component.defines = info["defines"]
            component.requires = list(dict.fromkeys(info["requires"]))
            component.system_libs = info["system_libs"]
        used = {r.split("::")[0] for c in self.cpp_info.components.values() for r in c.requires if "::" in r}
        direct = {dep.ref.name for dep in self.dependencies.direct_host.values()}
        self.cpp_info.ignored_requires = [
            dep for dep in ("libtiff", "libpng", "freetype", "meshoptimizer", "xxhash", "sqlite3", "qt", "mcpp", "expat",
                            "azslc", "directx-shader-compiler")
            if dep in direct and dep not in used]
