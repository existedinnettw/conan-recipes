import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, replace_in_file, rmdir
from conan.tools.gnu import PkgConfigDeps


class LvglConan(ConanFile):
    name = "lvgl"
    description = "LVGL: Light and Versatile Graphics Library for embedded GUIs"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://lvgl.io"
    topics = ("gui", "graphics", "embedded", "display", "widgets", "sdl", "wayland", "drm")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    # LVGL is configured at compile time through lv_conf.h. The package builds
    # with LV_CONF_SKIP instead and turns these options into -DLV_* defines,
    # which are exported to consumers too, since they size LVGL's structs.
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "color_format": ["I1", "L8", "RGB565", "RGB888", "XRGB8888", "ARGB8888"],
        "mem_size": ["ANY"],
        "stdlib": ["builtin", "clib"],
        "os_backend": ["none", "pthread", "windows"],
        "log_level": ["none", "trace", "info", "warn", "error", "user"],
        "with_sdl": [True, False],
        "with_linux_fbdev": [True, False],
        "with_linux_drm": [True, False],
        "with_wayland": [True, False],
        "with_evdev": [True, False],
        "with_thorvg": [True, False],
        "with_demos": [True, False],
        # Any other lv_conf.h setting, as "NAME=VALUE;NAME=VALUE".
        "extra_defines": ["ANY"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "color_format": "RGB565",
        # LVGL's own default (64 KB) is too small for the widgets demo.
        "mem_size": "262144",
        "stdlib": "builtin",
        "os_backend": "none",
        "log_level": "none",
        "with_sdl": False,
        "with_linux_fbdev": False,
        "with_linux_drm": False,
        "with_wayland": False,
        "with_evdev": False,
        "with_thorvg": True,
        "with_demos": True,
        "extra_defines": "",
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        if self.settings.os != "Linux":
            self.options.rm_safe("with_linux_fbdev")
            self.options.rm_safe("with_linux_drm")
            self.options.rm_safe("with_wayland")
            self.options.rm_safe("with_evdev")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # ThorVG is the only C++ in LVGL.
        if not self.options.with_thorvg:
            self.settings.rm_safe("compiler.cppstd")
            self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_sdl:
            self.requires("sdl/[>=2.28 <3]")
        if self.options.get_safe("with_linux_drm"):
            self.requires("libdrm/2.4.124")
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.22]")
            # Pinned like sdl's own xkbcommon requirement, so both backends fit
            # in one graph.
            self.requires("xkbcommon/1.6.0")

    def build_requirements(self):
        if self.options.get_safe("with_wayland"):
            self.tool_requires("wayland/<host_version>")  # wayland-scanner
            self.tool_requires("wayland-protocols/[^1.33]")
            if not self.conf.get("tools.gnu:pkg_config", check_type=str):
                self.tool_requires("pkgconf/[>=2.2 <3]")

    def validate(self):
        if self.options.os_backend == "windows" and self.settings.os != "Windows":
            raise ConanInvalidConfiguration("os_backend=windows needs a Windows host")
        if self.options.os_backend == "pthread" and self.settings.os == "Windows":
            raise ConanInvalidConfiguration("os_backend=pthread is not available on Windows")
        if not str(self.options.mem_size).isdigit():
            raise ConanInvalidConfiguration("mem_size must be a number of bytes")
        for define in self._extra_defines:
            if not define.split("=", 1)[0].startswith("LV_"):
                raise ConanInvalidConfiguration(f"extra_defines: {define!r} is not an LV_* setting")

    @property
    def _extra_defines(self):
        return [d.strip() for d in str(self.options.extra_defines).split(";") if d.strip()]

    @property
    def _public_defines(self):
        o = self.options
        stdlib = "LV_STDLIB_BUILTIN" if o.stdlib == "builtin" else "LV_STDLIB_CLIB"
        defines = {
            "LV_CONF_SKIP": None,
            "LV_COLOR_FORMAT_DEFAULT": f"LV_COLOR_FORMAT_{o.color_format}",
            "LV_USE_STDLIB_MALLOC": stdlib,
            "LV_USE_STDLIB_STRING": stdlib,
            "LV_USE_STDLIB_SPRINTF": stdlib,
            "LV_MEM_SIZE": str(o.mem_size),
            "LV_USE_OS": f"LV_OS_{str(o.os_backend).upper()}",
        }
        if o.log_level != "none":
            defines["LV_USE_LOG"] = "1"
            defines["LV_LOG_LEVEL"] = f"LV_LOG_LEVEL_{str(o.log_level).upper()}"
        if o.with_sdl:
            defines["LV_USE_SDL"] = "1"
        for option, define in (
            ("with_linux_fbdev", "LV_USE_LINUX_FBDEV"),
            ("with_linux_drm", "LV_USE_LINUX_DRM"),
            ("with_wayland", "LV_USE_WAYLAND"),
            ("with_evdev", "LV_USE_EVDEV"),
        ):
            if o.get_safe(option):
                defines[define] = "1"
        if o.with_thorvg:
            defines.update({
                "LV_USE_FLOAT": "1",
                "LV_USE_MATRIX": "1",
                "LV_USE_VECTOR_GRAPHIC": "1",
                "LV_USE_THORVG": "1",
                "LV_USE_THORVG_INTERNAL": "1",
                "LV_USE_SVG": "1",
                "LV_USE_LOTTIE": "1",
            })
            if o.os_backend != "none":
                # lv_conf_internal.h insists on 32 KB for ThorVG's draw thread.
                defines["LV_DRAW_THREAD_STACK_SIZE"] = str(32 * 1024)
        if o.with_demos:
            defines.update({
                "LV_BUILD_DEMOS": "1",
                "LV_USE_DEMO_WIDGETS": "1",
                "LV_USE_DEMO_BENCHMARK": "1",
                "LV_USE_DEMO_KEYPAD_AND_ENCODER": "1",
                "LV_USE_DEMO_MUSIC": "1",
                "LV_USE_DEMO_RENDER": "1",
                "LV_USE_DEMO_STRESS": "1",
            })
            if o.with_thorvg:
                defines["LV_USE_DEMO_VECTOR_GRAPHIC"] = "1"
            # The fonts the demos above use; the benchmark refuses to build
            # without 14, 20, 24 and 26.
            for size in (12, 14, 16, 18, 20, 22, 24, 26, 32):
                defines[f"LV_FONT_MONTSERRAT_{size}"] = "1"
        else:
            defines["LV_BUILD_DEMOS"] = "0"
        # Left last, so they can override anything above.
        for define in self._extra_defines:
            name, _, value = define.partition("=")
            defines[name.strip()] = value.strip() or None
        return defines

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _patch_sources(self):
        # The Wayland protocol XMLs are looked up under /usr/share or a Yocto
        # sysroot only; take them from the wayland-protocols package instead.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "env_support", "cmake", "dependencies", "wayland.cmake"),
            "if(DEFINED ENV{SDKTARGETSYSROOT})\n  set(PROTOCOL_ROOT",
            "if(LV_WAYLAND_PROTOCOLS_DIR)\n  set(PROTOCOL_ROOT \"${LV_WAYLAND_PROTOCOLS_DIR}\")\n"
            "elseif(DEFINED ENV{SDKTARGETSYSROOT})\n  set(PROTOCOL_ROOT",
        )

    def generate(self):
        VirtualBuildEnv(self).generate()

        tc = CMakeToolchain(self)
        for name, value in self._public_defines.items():
            tc.preprocessor_definitions[name] = value
        tc.cache_variables["LV_CONF_SKIP"] = True
        tc.cache_variables["LV_BUILD_INSTALL"] = True
        tc.cache_variables["LV_BUILD_TESTS"] = False
        tc.cache_variables["LV_FETCH_DEPENDENCIES"] = False
        # With LV_CONF_SKIP nothing parses the config, so the CONFIG_LV_* switches
        # that pick sources and dependencies have to be set by hand. evdev is left
        # out on purpose: the driver needs only <linux/input.h>, but setting
        # CONFIG_LV_USE_EVDEV would make the build demand libevdev.
        tc.cache_variables["CONFIG_LV_BUILD_EXAMPLES"] = False
        tc.cache_variables["CONFIG_LV_BUILD_DEMOS"] = bool(self.options.with_demos)
        tc.cache_variables["CONFIG_LV_USE_THORVG"] = bool(self.options.with_thorvg)
        tc.cache_variables["CONFIG_LV_USE_THORVG_INTERNAL"] = bool(self.options.with_thorvg)
        tc.cache_variables["CONFIG_LV_USE_SDL"] = bool(self.options.with_sdl)
        tc.cache_variables["CONFIG_LV_USE_LINUX_DRM"] = bool(self.options.get_safe("with_linux_drm"))
        tc.cache_variables["CONFIG_LV_USE_WAYLAND"] = bool(self.options.get_safe("with_wayland"))
        # The demos include LVGL's private headers, which include the backends'
        # own (<xf86drmMode.h>, <SDL2/SDL.h>...); upstream turns this on for
        # them too, which also links the backends PUBLIC.
        tc.cache_variables["CONFIG_LV_USE_PRIVATE_API"] = bool(self.options.with_demos)
        # Conan Center's wayland and xkbcommon do not provide the Wayland::* and
        # Xkbcommon::* targets LVGL expects from find_package; use pkg-config.
        tc.cache_variables["LV_USE_FIND_PACKAGE_WAYLAND"] = False
        tc.cache_variables["LV_USE_FIND_PACKAGE_XKBCOMMON"] = False
        if self.options.get_safe("with_wayland"):
            protocols = self.dependencies.build["wayland-protocols"]
            tc.cache_variables["LV_WAYLAND_PROTOCOLS_DIR"] = os.path.join(
                protocols.package_folder, "res", "wayland-protocols").replace("\\", "/")
        else:
            tc.cache_variables["LV_USE_PKG_CONFIG"] = False
        tc.generate()

        CMakeDeps(self).generate()
        if self.options.get_safe("with_wayland"):
            PkgConfigDeps(self).generate()

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENCE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.options.with_thorvg:
            copy(self, "LICENSE.txt", os.path.join(self.source_folder, "src", "libs", "thorvg"),
                 os.path.join(self.package_folder, "licenses", "thorvg"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lvgl")
        self.cpp_info.set_property("pkg_config_name", "lvgl")

        defines = [name if value is None else f"{name}={value}"
                   for name, value in self._public_defines.items()]

        core = self.cpp_info.components["lvgl_core"]
        core.set_property("cmake_target_name", "lvgl::lvgl")
        core.set_property("pkg_config_name", "lvgl")
        core.libs = ["lvgl"]
        if self.options.with_thorvg:
            core.libs.append("lvgl_thorvg")
        core.defines = defines
        if self.settings.os in ("Linux", "FreeBSD"):
            core.system_libs = ["m"]
            if self.options.os_backend == "pthread":
                core.system_libs.append("pthread")
        if self.options.with_thorvg and not self.options.shared and stdcpp_library(self):
            core.system_libs.append(stdcpp_library(self))
        if self.options.with_sdl:
            core.requires.append("sdl::libsdl2")
        if self.options.get_safe("with_linux_drm"):
            core.requires.append("libdrm::libdrm_libdrm")
        if self.options.get_safe("with_wayland"):
            core.requires.extend([
                "wayland::wayland-client",
                "wayland::wayland-cursor",
                "xkbcommon::libxkbcommon",
            ])

        if self.options.with_demos:
            demos = self.cpp_info.components["lvgl_demos"]
            demos.set_property("cmake_target_name", "lvgl::lvgl_demos")
            demos.set_property("cmake_target_aliases", ["lvgl::demos"])
            demos.set_property("pkg_config_name", "lvgl_demos")
            demos.libs = ["lvgl_demos"]
            # The installed demo headers reach lvgl's headers with paths like
            # "../../include/lvgl/draw/lv_draw.h", relative to the source tree.
            demos.includedirs = ["include", os.path.join("include", "lvgl")]
            demos.requires = ["lvgl_core"]
