import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir

required_conan_version = ">=2.0"


class Coin3DConan(ConanFile):
    # Named coin3d, not coin: the coin-* recipes on Conan Center are COIN-OR.
    name = "coin3d"
    license = "BSD-3-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/coin3d/coin"
    description = "Coin3D: OpenGL-based, retained-mode 3D graphics library implementing the Open Inventor 2.1 API"
    topics = ("open-inventor", "opengl", "scene-graph", "3d", "graphics", "vrml", "freecad")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "threadsafe": [True, False],
        "with_vrml97": [True, False],
        "with_nodekits": [True, False],
        "with_3ds_import": [True, False],
        "with_zlib": [True, False],
        "with_bzip2": [True, False],
        "with_freetype": [True, False],
        "with_fontconfig": [True, False],
        "with_openal": [True, False],
        # Off-screen rendering contexts on Linux.
        "with_glx": [True, False],
        "with_egl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "threadsafe": False,
        "with_vrml97": True,
        "with_nodekits": True,
        "with_3ds_import": True,
        "with_zlib": True,
        "with_bzip2": True,
        "with_freetype": True,
        "with_fontconfig": True,
        "with_openal": False,
        "with_glx": True,
        "with_egl": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        if self.settings.os not in ("Linux", "FreeBSD"):
            del self.options.with_fontconfig
            del self.options.with_glx
            del self.options.with_egl

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Coin finds OpenGL, EGL and X11 with CMake's own find modules; these make sure
        # the system development packages are installed.
        self.requires("opengl/system")
        if self.options.get_safe("with_egl"):
            self.requires("egl/system")
        if self.options.get_safe("with_glx"):
            self.requires("xorg/system")
        # Upstream bundles expat; use Conan Center's instead.
        self.requires("expat/[>=2.6 <3]")
        if self.options.with_zlib:
            self.requires("zlib/[>=1.2.11 <2]")
        if self.options.with_bzip2:
            self.requires("bzip2/1.0.8")
        if self.options.with_freetype:
            self.requires("freetype/2.14.3")
        if self.options.get_safe("with_fontconfig"):
            self.requires("fontconfig/2.17.1")
        if self.options.with_openal:
            self.requires("openal-soft/1.24.3")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["COIN_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["COIN_BUILD_TESTS"] = False
        tc.cache_variables["COIN_BUILD_EXAMPLES"] = False
        tc.cache_variables["COIN_BUILD_DOCUMENTATION"] = False
        tc.cache_variables["COIN_USE_CPACK"] = False
        tc.cache_variables["COIN_THREADSAFE"] = bool(self.options.threadsafe)
        tc.cache_variables["HAVE_VRML97"] = bool(self.options.with_vrml97)
        # SpiderMonkey (JavaScript in VRML97 scripts) has no recipe.
        tc.cache_variables["COIN_HAVE_JAVASCRIPT"] = False
        tc.cache_variables["HAVE_NODEKITS"] = bool(self.options.with_nodekits)
        tc.cache_variables["HAVE_3DS_IMPORT_CAPABILITIES"] = bool(self.options.with_3ds_import)
        tc.cache_variables["HAVE_SOUND"] = bool(self.options.with_openal)
        tc.cache_variables["USE_EXTERNAL_EXPAT"] = True
        tc.cache_variables["COIN_BUILD_GLX"] = bool(self.options.get_safe("with_glx", False))
        tc.cache_variables["COIN_BUILD_EGL"] = bool(self.options.get_safe("with_egl", False))
        tc.cache_variables["COIN_BUILD_MSVC_STATIC_RUNTIME"] = self.settings.get_safe("compiler.runtime") == "static"
        # By default Coin dlopen()s its optional libraries at run time; link the Conan
        # packages instead. Disabled ones then stay disabled.
        tc.cache_variables["ZLIB_RUNTIME_LINKING"] = False
        tc.cache_variables["LIBBZIP2_RUNTIME_LINKING"] = False
        tc.cache_variables["FREETYPE_RUNTIME_LINKING"] = False
        tc.cache_variables["FONTCONFIG_RUNTIME_LINKING"] = False
        tc.cache_variables["OPENAL_RUNTIME_LINKING"] = False
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_ZLIB"] = not self.options.with_zlib
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_BZip2"] = not self.options.with_bzip2
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Freetype"] = not self.options.with_freetype
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Fontconfig"] = not self.options.get_safe("with_fontconfig", False)
        # GLU and simage (image file loading) have no Conan packages that fit and stay
        # loaded at run time if the system has them.
        tc.cache_variables["GLU_RUNTIME_LINKING"] = True
        tc.cache_variables["SIMAGE_RUNTIME_LINKING"] = True
        tc.generate()
        deps = CMakeDeps(self)
        # Coin makes its own EXPAT::EXPAT from EXPAT_LIBRARIES unless the target exists.
        deps.set_property("expat", "cmake_target_name", "EXPAT::EXPAT")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # Data files (dragger geometry, shaders, SCXML) are compiled into the library too.
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "coin-config", os.path.join(self.package_folder, "bin"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir) and not os.listdir(bindir):
            rmdir(self, bindir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Coin")
        self.cpp_info.set_property("cmake_target_name", "Coin::Coin")
        self.cpp_info.set_property("pkg_config_name", "Coin")

        lib = "Coin"
        if self.settings.os == "Windows" and self.settings.compiler != "gcc":
            # The major version, plus "s" for the static library and "d" for Debug.
            lib += "4" if self.options.shared else "4s"
        if self.settings.os == "Windows" and self.settings.build_type == "Debug":
            lib += "d"
        self.cpp_info.libs = [lib]

        if self.settings.os == "Windows":
            self.cpp_info.defines = ["COIN_DLL" if self.options.shared else "COIN_NOT_DLL"]
            if not self.options.shared:
                self.cpp_info.system_libs = ["gdi32", "user32"]
        elif self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        elif self.settings.os == "Macos":
            self.cpp_info.frameworks = ["CoreFoundation", "CoreGraphics"]
