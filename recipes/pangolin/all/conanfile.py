import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir, save


class PangolinConan(ConanFile):
    name = "pangolin"
    description = (
        "Pangolin: a lightweight portable library for prototyping 3D, numeric or video "
        "based programs and algorithms (OpenGL display, interaction and video input)"
    )
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/stevenlovegrove/Pangolin"
    topics = ("opengl", "gui", "visualization", "video", "plotting", "computer-vision")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_png": [True, False],
        "with_jpeg": [True, False],
        "with_tiff": [True, False],
        "with_lz4": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_png": True,
        "with_jpeg": True,
        "with_tiff": False,
        "with_lz4": False,
    }

    # Every components/<name>/CMakeLists.txt is one library; public link dependencies
    # between them as declared upstream.
    _components = {
        "pango_core": [],
        "pango_vars": ["pango_core"],
        "pango_image": ["pango_core"],
        "pango_opengl": ["pango_core", "pango_image"],
        "pango_windowing": ["pango_core", "pango_opengl"],
        "pango_display": ["pango_core", "pango_opengl", "pango_windowing", "pango_vars"],
        "pango_plot": ["pango_display"],
        "pango_packetstream": ["pango_core"],
        "pango_video": ["pango_core", "pango_image", "pango_packetstream"],
        "tinyobj": [],
        "pango_geometry": ["pango_core", "pango_image", "tinyobj"],
        "pango_glgeometry": ["pango_geometry", "pango_opengl"],
        "pango_scene": ["pango_opengl"],
        "pango_tools": ["pango_display", "pango_video"],
        # Built without Python; upstream still installs it as an empty library.
        "pango_python": [],
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("sigslot/1.2.3", transitive_headers=True)
        self.requires("opengl/system", transitive_headers=True, transitive_libs=True)
        self.requires("egl/system", transitive_headers=True, transitive_libs=True)
        self.requires("libepoxy/1.5.10", transitive_headers=True, transitive_libs=True)
        self.requires("xorg/system")
        if self.options.with_png:
            self.requires("libpng/[>=1.6 <2]")
        if self.options.with_jpeg:
            self.requires("libjpeg/[>=9e]")
        if self.options.with_tiff:
            self.requires("libtiff/[>=4.6.0 <5]")
        if self.options.with_lz4:
            self.requires("lz4/[>=1.9.4 <2]")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} recipe is only validated on Linux")
        check_min_cppstd(self, 17)
        if not self.dependencies["libepoxy"].options.egl:
            raise ConanInvalidConfiguration(f"{self.ref} requires libepoxy/*:egl=True")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Vendored palacaze/sigslot 1.2.x comes from Conan instead (as vcpkg does).
        rmdir(self, os.path.join(self.source_folder, "components", "pango_core", "include", "sigslot"))

        top = os.path.join(self.source_folder, "CMakeLists.txt")
        # No -Werror in a package build; newer compilers add warnings upstream does not fix.
        replace_in_file(self, top, "add_compile_options(-Wall -Wextra -Werror)", "add_compile_options(-Wall -Wextra)")
        replace_in_file(self, top, "        add_compile_options(-Werror=maybe-uninitialized)\n", "")
        replace_in_file(self, top, "    add_compile_options(-Werror=vla)\n", "")

        core = os.path.join(self.source_folder, "components", "pango_core", "CMakeLists.txt")
        replace_in_file(self, core, "find_package(Threads QUIET)",
                        "find_package(PalSigslot CONFIG REQUIRED)\n"
                        "target_link_libraries(${COMPONENT} PUBLIC Pal::Sigslot)\n\n"
                        "find_package(Threads QUIET)")

        # Link OpenGL, EGL, epoxy and X11 through the Conan targets instead of FindOpenGL
        # (which needs GLVND's libOpenGL.so), FindX11 and a pkg-config based Findepoxy.
        opengl = os.path.join(self.source_folder, "components", "pango_opengl", "CMakeLists.txt")
        replace_in_file(self, opengl,
                        "        find_package(OpenGL REQUIRED COMPONENTS OpenGL EGL)\n"
                        "        find_package(epoxy REQUIRED)\n"
                        "        target_link_libraries(${COMPONENT} PUBLIC OpenGL::OpenGL OpenGL::EGL)\n"
                        "        target_link_libraries(${COMPONENT} PUBLIC ${epoxy_LIBRARIES})\n"
                        "        target_include_directories(${COMPONENT} PUBLIC $<BUILD_INTERFACE:${epoxy_INCLUDE_DIRS}>)\n",
                        "        find_package(opengl_system REQUIRED CONFIG)\n"
                        "        find_package(egl REQUIRED CONFIG)\n"
                        "        find_package(libepoxy REQUIRED CONFIG)\n"
                        "        target_link_libraries(${COMPONENT} PUBLIC opengl::opengl egl::egl libepoxy::libepoxy)\n")

        windowing = os.path.join(self.source_folder, "components", "pango_windowing", "CMakeLists.txt")
        replace_in_file(self, windowing,
                        "    find_package(X11 QUIET)\n"
                        "    find_package(OpenGL QUIET COMPONENTS EGL)\n"
                        "    if(X11_FOUND AND OpenGL_EGL_FOUND)\n"
                        "        target_sources( ${COMPONENT} PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src/display_x11.cpp )\n"
                        "        target_link_libraries(${COMPONENT} PRIVATE ${X11_LIBRARIES} )\n"
                        "        target_include_directories(${COMPONENT} PRIVATE ${X11_INCLUDE_DIR} )\n"
                        "        target_link_libraries(${COMPONENT} PRIVATE OpenGL::EGL)\n",
                        "    find_package(xorg REQUIRED CONFIG)\n"
                        "    find_package(egl REQUIRED CONFIG)\n"
                        "    if(TRUE)\n"
                        "        target_sources( ${COMPONENT} PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src/display_x11.cpp )\n"
                        "        target_link_libraries(${COMPONENT} PRIVATE xorg::x11 egl::egl)\n")
        # Wayland windowing is not packaged (needs wayland, wayland-protocols, xkbcommon).
        replace_in_file(self, windowing,
                        "    find_package(PkgConfig)\n"
                        "    pkg_check_modules(WAYLAND_CLIENT wayland-client QUIET)\n"
                        "    pkg_check_modules(wayland-protocols QUIET wayland-protocols>=1.13)\n"
                        "    if(WAYLAND_CLIENT_FOUND AND wayland-protocols_FOUND)\n",
                        "    if(FALSE)\n")
        replace_in_file(self, windowing,
                        "find_package(OpenGL QUIET COMPONENTS EGL)\n"
                        "if(OpenGL_EGL_FOUND)\n"
                        "    target_sources( ${COMPONENT} PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src/display_headless.cpp )\n"
                        "    target_link_libraries(${COMPONENT} PRIVATE ${OPENGL_egl_LIBRARY} )\n",
                        "if(TRUE)\n"
                        "    target_sources( ${COMPONENT} PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src/display_headless.cpp )\n"
                        "    target_link_libraries(${COMPONENT} PRIVATE egl::egl)\n")

        image = os.path.join(self.source_folder, "components", "pango_image", "CMakeLists.txt")
        replace_in_file(self, image, "${PNG_LIBRARY} ${ZLIB_LIBRARY}", "PNG::PNG")
        replace_in_file(self, image, "${JPEG_LIBRARY}", "JPEG::JPEG")
        replace_in_file(self, image, "${TIFF_LIBRARY}", "TIFF::TIFF")
        save(self, os.path.join(self.source_folder, "cmake", "FindLz4.cmake"), textwrap.dedent("""\
            find_package(lz4 CONFIG)
            set(Lz4_FOUND ${lz4_FOUND})
            set(Lz4_INCLUDE_DIRS "")
            set(Lz4_LIBRARIES lz4::lz4)
        """))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TOOLS"] = False
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["BUILD_PANGOLIN_PYTHON"] = False
        tc.cache_variables["BUILD_PANGOLIN_LIBPNG"] = self.options.with_png
        tc.cache_variables["BUILD_PANGOLIN_LIBJPEG"] = self.options.with_jpeg
        tc.cache_variables["BUILD_PANGOLIN_LIBTIFF"] = self.options.with_tiff
        tc.cache_variables["BUILD_PANGOLIN_LZ4"] = self.options.with_lz4
        for flag in ("LIBOPENEXR", "ZSTD", "LIBRAW", "LIBDC1394", "FFMPEG", "REALSENSE", "REALSENSE2",
                     "OPENNI", "OPENNI2", "LIBUVC", "UVC_MEDIAFOUNDATION", "DEPTHSENSE", "TELICAM", "PLEORA"):
            tc.cache_variables[f"BUILD_PANGOLIN_{flag}"] = False
        tc.cache_variables["BUILD_PANGOLIN_V4L"] = True
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENCE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # Upstream's config sets Pangolin_LIBRARIES to every component, which is what
        # consumers like basalt link; provide the same variable.
        save(self, os.path.join(self.package_folder, self._module_file_rel_path),
             "set(Pangolin_LIBRARIES {0})\nset(Pangolin_LIBRARY {0})\n".format(" ".join(self._components)))

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", "conan-pangolin-variables.cmake")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Pangolin")
        self.cpp_info.set_property("cmake_target_name", "Pangolin::Pangolin")
        self.cpp_info.set_property("cmake_build_modules", [self._module_file_rel_path])

        for name, deps in self._components.items():
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", name)
            component.libs = [name]
            component.requires = list(deps)

        core = self.cpp_info.components["pango_core"]
        core.requires.append("sigslot::sigslot")
        core.defines = ["_LINUX_"]
        core.system_libs = ["pthread", "rt", "dl"]

        image = self.cpp_info.components["pango_image"]
        image.requires.append("eigen::eigen")
        image.defines = ["HAVE_EIGEN"]
        if self.options.with_png:
            image.requires.append("libpng::libpng")
        if self.options.with_jpeg:
            image.requires.append("libjpeg::libjpeg")
        if self.options.with_tiff:
            image.requires.append("libtiff::libtiff")
        if self.options.with_lz4:
            image.requires.append("lz4::lz4")

        opengl = self.cpp_info.components["pango_opengl"]
        opengl.requires.extend(["eigen::eigen", "opengl::opengl", "egl::egl", "libepoxy::libepoxy"])
        opengl.defines = ["HAVE_EIGEN", "HAVE_EPOXY"]

        self.cpp_info.components["pango_windowing"].requires.extend(["xorg::x11", "egl::egl"])

        geometry = self.cpp_info.components["pango_geometry"]
        geometry.requires.append("eigen::eigen")
        geometry.defines = ["HAVE_EIGEN"]
