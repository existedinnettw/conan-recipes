import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rm, rmdir, save
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.system import package_manager

# get(excludes=...) needs Conan 2.20.
required_conan_version = ">=2.20"


class FilamentConan(ConanFile):
    name = "filament"
    description = ("Real-time physically based rendering engine for Android, iOS, Windows, Linux, "
                   "macOS and WebGL2, with its material compiler and asset tools")
    license = "Apache-2.0"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/google/filament"
    topics = ("rendering", "pbr", "3d", "opengl", "vulkan", "gltf", "graphics")
    # Upstream only builds static libraries.
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "with_opengl": [True, False],
        "with_vulkan": [True, False],
        # Linux: the windowing system the OpenGL and Vulkan platforms are built for. Upstream
        # supports one at a time; "egl" is headless (EGL for OpenGL, no window system).
        "window_system": ["x11", "wayland", "egl"],
        # WebP textures in glTF files (EXT_texture_webp).
        "with_webp": [True, False],
    }
    default_options = {
        "fPIC": True,
        "with_opengl": True,
        "with_vulkan": True,
        "window_system": "x11",
        "with_webp": False,
    }

    def export_sources(self):
        copy(self, "conan_deps.cmake", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
            # Like upstream, which has no Vulkan backend on Windows by default.
            self.options.with_vulkan = False
        if self.settings.os != "Linux":
            self.options.rm_safe("window_system")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Public headers: utils includes tsl/robin_map.h, filagui and viewer include imgui.h.
        self.requires("tsl-robin-map/[>=1.3.0 <2]", transitive_headers=True)
        self.requires("imgui/1.92.5", transitive_headers=True)
        self.requires("zstd/[>=1.5 <1.6]")
        self.requires("draco/[>=1.5.6 <2]")
        self.requires("meshoptimizer/[>=0.18 <2]")
        self.requires("mikktspace/cci.20200325")
        self.requires("cgltf/[>=1.13 <2]")
        self.requires("jsmn/1.1.0")
        self.requires("stb/cci.20240531")
        # Only the tools (imageio, assimp, tinyexr) use libpng and zlib.
        self.requires("libpng/[>=1.6 <2]")
        self.requires("zlib/[>=1.2.11 <2]")
        if self.options.with_webp:
            self.requires("libwebp/[>=1.3 <2]")
        # Linux platforms: Xlib, xcb, libGL and libvulkan are loaded at run time, but their
        # headers are needed.
        for reference in sorted({p[0] for p in self._backend_system_packages}):
            self.requires(reference)

    def validate(self):
        check_min_cppstd(self, 20)
        if self.settings.os not in ("Linux", "Windows"):
            raise ConanInvalidConfiguration(f"{self.ref} recipe only supports Linux and Windows")
        if cross_building(self):
            # matc, resgen and others run during the build; upstream imports them from a host
            # build when cross-compiling, which this recipe does not do yet.
            raise ConanInvalidConfiguration(f"{self.ref} recipe does not support cross-building")
        if self.settings.os == "Windows" and not is_msvc(self):
            raise ConanInvalidConfiguration(f"{self.ref} only supports MSVC on Windows")
        if not self.options.with_opengl and not self.options.with_vulkan:
            raise ConanInvalidConfiguration(f"{self.ref} needs with_opengl or with_vulkan")
        if self.settings.os == "Linux" and self.options.window_system == "wayland" and \
                not self.options.with_vulkan:
            # Upstream has no OpenGL platform for Wayland.
            raise ConanInvalidConfiguration(f"{self.ref} needs with_vulkan with window_system=wayland")

    def system_requirements(self):
        if self.settings.os == "Linux" and self.options.with_opengl and \
                self.options.window_system == "egl":
            # OpenGL ES headers and libGLESv2, which egl/system does not install.
            package_manager.Apt(self).install_substitutes(
                ["libgles-dev"], ["libgles2-mesa-dev"], update=True, check=True)
            package_manager.PacMan(self).install(["libglvnd"], update=True, check=True)
            package_manager.Dnf(self).install(["libglvnd-devel"], update=True, check=True)
            package_manager.Yum(self).install(["libglvnd-devel"], update=True, check=True)
            package_manager.Zypper(self).install(["Mesa-libGLESv2-devel", "Mesa-libGLESv3-devel"],
                                                 update=True, check=True)
            package_manager.Apk(self).install(["mesa-dev"], update=True, check=True)

    def source(self):
        # Libraries taken from Conan, test, sample and WebGPU (Dawn) dependencies and assets are
        # most of the archive.
        # fnmatch's "*" also matches "/"; the archive root anchors the top-level directories.
        root = f"filament-{self.version}"
        get(self, **self.conan_data["sources"][self.version], strip_root=True,
            excludes=[f"{root}/third_party/{lib}/*" for lib in (
                "abseil", "benchmark", "cgltf", "dawn", "draco", "environments", "gl-matrix",
                "gltumble", "imgui", "jsmn", "libgtest", "libpng", "libsdl2", "libwebp", "libz",
                "markdeep", "meshoptimizer", "mikktspace", "models", "perfetto", "robin-map",
                "textures", "zstd")]
            # stb: only upstream's stb_image.cpp (the implementation) is used.
            + [f"{root}/third_party/stb/*.h", f"{root}/third_party/stb/deprecated/*"]
            + [f"{root}/{d}/*" for d in ("android", "art", "docs", "docs_src", "ios", "samples",
                                          "test", "web")])
        self._patch_sources()

    def _patch_sources(self):
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        for subdir in ("${EXTERNAL}/libgtest/tnt", "${EXTERNAL}/abseil/tnt", "${EXTERNAL}/zstd/tnt",
                       "${EXTERNAL}/imgui/tnt", "${EXTERNAL}/robin-map/tnt", "${EXTERNAL}/benchmark/tnt",
                       "${EXTERNAL}/meshoptimizer/tnt", "${EXTERNAL}/mikktspace", "${EXTERNAL}/cgltf/tnt",
                       "${EXTERNAL}/draco/tnt", "${EXTERNAL}/jsmn/tnt", "${EXTERNAL}/stb/tnt",
                       "${EXTERNAL}/perfetto/tnt", "${EXTERNAL}/libwebp/tnt", "${EXTERNAL}/libpng/tnt",
                       "${EXTERNAL}/libsdl2/tnt", "${EXTERNAL}/libz/tnt", "${FILAMENT}/samples",
                       "${LIBRARIES}/filamentapp"):
            replace_in_file(self, cmakelists, f"add_subdirectory({subdir})", "")
        # Tests and benchmarks that FILAMENT_BUILD_TESTING does not turn off.
        filament_cmakelists = os.path.join(self.source_folder, "filament", "CMakeLists.txt")
        replace_in_file(self, filament_cmakelists, "add_subdirectory(test)", "")
        replace_in_file(self, filament_cmakelists, "add_subdirectory(benchmark)", "")
        for lib in ("imagediff", "imageio-lite"):
            replace_in_file(self, os.path.join(self.source_folder, "libs", lib, "CMakeLists.txt"),
                            "if (NOT ANDROID AND NOT WASM AND NOT IOS)\n    add_executable(test_",
                            "if (FILAMENT_BUILD_TESTING AND NOT ANDROID AND NOT WASM AND NOT IOS)\n"
                            "    add_executable(test_")
        # GCC ("unsupported" upstream): a missing include and a Clang-only flag.
        replace_in_file(self, os.path.join(self.source_folder, "libs", "filamat", "src", "eiff", "BlobDictionary.h"),
                        "#include <vector>", "#include <cstdint>\n#include <vector>")
        for lib in ("iblprefilter", "generatePrefilterMipmap"):
            replace_in_file(self, os.path.join(self.source_folder, "libs", lib, "CMakeLists.txt"),
                            "        -fstrict-vtable-pointers\n",
                            "        $<$<CXX_COMPILER_ID:Clang,AppleClang>:-fstrict-vtable-pointers>\n")
        # Conan's cgltf library already has the implementation.
        replace_in_file(self, os.path.join(self.source_folder, "libs", "gltfio", "src", "Utility.cpp"),
                        "#define CGLTF_IMPLEMENTATION\n", "")
        # viewer needs filagui, which upstream does not install.
        save(self, os.path.join(self.source_folder, "libs", "filagui", "CMakeLists.txt"),
             "\ninstall(TARGETS ${TARGET} ARCHIVE DESTINATION lib/${DIST_DIR})\n"
             "install(DIRECTORY ${PUBLIC_HDR_DIR}/filagui DESTINATION include)\n", append=True)
        copy(self, "conan_deps.cmake", self.export_sources_folder, self.source_folder)

    @property
    def _matdbg(self):
        # Upstream's FILAMENT_ENABLE_MATDBG default: the material debugger is linked into
        # libfilament in Debug builds.
        return self.settings.build_type == "Debug"

    @property
    def _backend_system_packages(self):
        # (reference, find_package() name, CMake target, Conan component) of the Linux platform
        # dependencies.
        if self.settings.os != "Linux":
            return []
        window_system = self.options.window_system
        packages = []
        if window_system == "x11":
            packages += [("xorg/system", "xorg", "xorg::x11", "xorg::x11"),
                         ("xorg/system", "xorg", "xorg::xcb", "xorg::xcb")]
            if self.options.with_opengl:
                packages.append(("opengl/system", "opengl_system", "opengl::opengl", "opengl::opengl"))
        elif window_system == "wayland":
            # Upstream has no OpenGL platform for Wayland; only the Vulkan backend can run there.
            packages.append(("wayland/[>=1.22 <2]", "wayland", "wayland::wayland-client",
                             "wayland::wayland-client"))
        elif window_system == "egl" and self.options.with_opengl:
            packages.append(("egl/system", "egl", "egl::egl", "egl::egl"))
        return packages

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_TNT_INCLUDE"] = os.path.join(self.source_folder, "conan_deps.cmake")
        tc.cache_variables["DIST_DIR"] = "."
        tc.cache_variables["FILAMENT_SKIP_SAMPLES"] = True
        tc.cache_variables["FILAMENT_SKIP_SDL2"] = True
        tc.cache_variables["FILAMENT_BUILD_TESTING"] = False
        tc.cache_variables["FILAMENT_ENABLE_PERFETTO"] = False
        tc.cache_variables["FILAMENT_USE_ABSEIL_LOGGING"] = False
        tc.cache_variables["FILAMENT_SUPPORTS_WEBGPU"] = False
        tc.cache_variables["FILAMENT_ENABLE_MATDBG"] = self._matdbg
        tc.cache_variables["FILAMENT_SUPPORTS_OPENGL"] = bool(self.options.with_opengl)
        tc.cache_variables["FILAMENT_SUPPORTS_VULKAN"] = bool(self.options.with_vulkan)
        tc.cache_variables["FILAMENT_SUPPORTS_WEBP_TEXTURES"] = bool(self.options.with_webp)
        if self.settings.os == "Linux":
            window_system = str(self.options.window_system)
            tc.cache_variables["FILAMENT_SUPPORTS_XCB"] = window_system == "x11"
            tc.cache_variables["FILAMENT_SUPPORTS_XLIB"] = window_system == "x11"
            tc.cache_variables["FILAMENT_SUPPORTS_WAYLAND"] = window_system == "wayland"
            # Upstream links the backend to EGL whenever this is on; without OpenGL, "egl" is a
            # headless Vulkan build.
            tc.cache_variables["FILAMENT_SUPPORTS_EGL_ON_LINUX"] = \
                window_system == "egl" and bool(self.options.with_opengl)
            tc.cache_variables["FILAMENT_CONAN_BACKEND_PACKAGES"] = ";".join(
                f"{package}={target}" for _, package, target, _ in self._backend_system_packages)
            # Upstream links libc++ and the C++ runtime statically; use the profile's libstdc++.
            tc.cache_variables["USE_STATIC_LIBCXX"] = False
        if self.settings.compiler == "gcc":
            # Upstream builds with Clang (and MSVC); GCC works but is "unsupported".
            tc.cache_variables["FILAMENT_ENABLE_EXPERIMENTAL_GCC_SUPPORT"] = True
        if is_msvc(self):
            tc.cache_variables["USE_STATIC_CRT"] = is_msvc_static_runtime(self)
            # Otherwise upstream adds /D_ITERATOR_DEBUG_LEVEL=0 to Debug builds, an ABI mismatch
            # (LNK2038) with consumers and dependencies built with the default level.
            tc.cache_variables["FILAMENT_SHORTEN_MSVC_COMPILATION"] = False
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        if self.settings.os == "Linux" and self.options.get_safe("window_system") == "egl" and \
                self.options.with_opengl:
            # The headless EGL backend uses OpenGL ES, which needs the "mobile" shader models;
            # upstream only compiles them for mobile targets (FILAMENT_LINUX_IS_MOBILE would also
            # drop the host tools such as matc). Build the materials for both.
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            "    set(MATC_TARGET desktop)", "    set(MATC_TARGET all)")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "docs"))
        # Sample assets of gltf_viewer, which is not built.
        rmdir(self, os.path.join(self.package_folder, "bin", "assets"))
        # Upstream's modified assimp, only linked into filamesh.
        rm(self, "*assimp*", os.path.join(self.package_folder, "lib"))
        for f in ("README.md", "LICENSE"):
            path = os.path.join(self.package_folder, f)
            if os.path.isfile(path):
                os.remove(path)

    def _add_component(self, name, libs=None, requires=None):
        component = self.cpp_info.components[name]
        component.set_property("cmake_target_name", f"filament::{name}")
        component.libs = libs if libs is not None else [name]
        if not component.libs:
            component.libdirs = []
        component.bindirs = []
        component.requires = requires or []
        return component

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "filament")
        # filament::filament is the engine component; this one links every component.
        self.cpp_info.set_property("cmake_target_name", "filament::all")

        utils = self._add_component("utils", requires=["tsl-robin-map::tsl-robin-map"])
        if self.settings.os == "Linux":
            utils.system_libs = ["dl", "pthread", "m"]
        elif self.settings.os == "Windows":
            utils.system_libs = ["shlwapi"]
        self._add_component("smol-v")
        self._add_component("filabridge", requires=["utils"])
        self._add_component("filaflat", requires=["filabridge", "smol-v"])
        backend_libs = ["backend"]
        if self.options.with_vulkan:
            backend_libs.append("bluevk")
        if self.options.with_opengl:
            backend_libs.append("bluegl")
        backend_requires = ["utils", "smol-v"]
        backend_requires += [component for *_, component in self._backend_system_packages]
        backend = self._add_component("backend", libs=backend_libs, requires=backend_requires)
        if self.settings.os == "Windows" and self.options.with_opengl:
            backend.system_libs = ["opengl32", "gdi32", "user32"]
        elif self.settings.os == "Linux" and self.options.with_opengl and \
                self.options.window_system == "egl":
            # With EGL, the backend calls OpenGL ES directly instead of through bluegl.
            backend.system_libs = ["GLESv2"]
        filament_requires = ["backend", "filaflat", "filabridge", "utils", "zstd::zstd"]
        if self._matdbg:
            filament_requires.append("matdbg")
        self._add_component("filament", requires=filament_requires)
        self._add_component("shaders")
        # Combined with upstream's glslang, SPIRV-Tools and SPIRV-Cross.
        self._add_component("filamat", requires=["filabridge", "utils", "shaders", "smol-v",
                                                 "zstd::zstd"])
        self._add_component("matp", requires=["filamat"])
        self._add_component("image", requires=["utils"])
        self._add_component("imageio-lite", requires=["image"])
        self._add_component("imagediff", requires=["image", "jsmn::jsmn"])
        self._add_component("ktxreader", libs=["ktxreader", "basis_transcoder"],
                            requires=["image", "filament", "zstd::zstd"])
        self._add_component("geometry", requires=["utils", "meshoptimizer::meshoptimizer",
                                                  "mikktspace::mikktspace"])
        self._add_component("camutils", requires=["utils"])
        self._add_component("ibl", requires=["utils"])
        self._add_component("ibl-lite", requires=["utils"])
        self._add_component("iblprefilter", libs=["filament-iblprefilter"], requires=["filament"])
        self._add_component("generatePrefilterMipmap", libs=["filament-generatePrefilterMipmap"],
                            requires=["ibl", "filament"])
        self._add_component("filameshio", requires=["filament", "meshoptimizer::meshoptimizer"])
        self._add_component("uberz", libs=["uberzlib"], requires=["filabridge", "zstd::zstd"])
        self._add_component("uberarchive", requires=["uberz"])
        gltfio_core_requires = ["filament", "geometry", "ktxreader", "uberz", "draco::draco",
                                "meshoptimizer::meshoptimizer", "zstd::zstd", "cgltf::cgltf",
                                "stb::stb"]
        if self.options.with_webp:
            gltfio_core_requires.append("libwebp::webpdecoder")
        self._add_component("gltfio_core", libs=["gltfio_core", "stb"], requires=gltfio_core_requires)
        # gltfio_core with JitShaderProvider, which compiles materials at run time.
        self._add_component("gltfio", requires=["gltfio_core", "filamat"])
        self._add_component("filagui", requires=["filament", "imgui::imgui"])
        self._add_component("civetweb")
        self._add_component("viewer", requires=["filagui", "gltfio_core", "imageio-lite", "civetweb",
                                                "jsmn::jsmn", "imgui::imgui"])
        # Combined with civetweb, SPIRV-Tools and SPIRV-Cross.
        self._add_component("matdbg", requires=["filamat", "filaflat", "filabridge", "utils"])

        # Executables (matc, cmgen, resgen, filamesh, mipgen, ...); their dependencies are
        # linked statically.
        tools = self.cpp_info.components["tools"]
        tools.libdirs = []
        tools.includedirs = []
        tools.bindirs = ["bin"]
        tools.requires = ["libpng::libpng", "zlib::zlib"]
