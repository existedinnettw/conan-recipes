import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, rename, replace_in_file, rm, rmdir

required_conan_version = ">=2.0"


class OrbbecSDKConan(ConanFile):
    name = "orbbecsdk"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/orbbec/OrbbecSDK_v2"
    description = "Orbbec SDK v2: C/C++ API for Orbbec 3D depth and color cameras over USB, Ethernet and GMSL"
    topics = ("orbbec", "depth-camera", "rgbd", "3d-camera", "point-cloud", "camera")
    # Upstream builds only a shared library.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"
    # USB and network device support are always built: the device code uses both
    # transports without checking OB_BUILD_USB_PAL/OB_BUILD_NET_PAL, so turning either
    # off leaves undefined symbols in the library.
    options = {
        # GMSL devices on NVIDIA Jetson.
        "with_gmsl": [True, False],
    }
    default_options = {
        "with_gmsl": True,
    }

    # Upstream ships its extensions (depth engine, filters, frame processor, firmware
    # updater) only as prebuilt binaries for these platforms. The SDK loads them at run
    # time from the "extensions" directory next to its own library.
    _extension_platforms = {
        ("Linux", "x86_64"),
        ("Linux", "armv8"),
        ("Windows", "x86_64"),
        ("Windows", "x86"),
        ("Macos", "x86_64"),
        ("Macos", "armv8"),
    }

    def config_options(self):
        if self.settings.os != "Linux":
            del self.options.with_gmsl

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        # The library exports only a C API; the C++ API is a header-only wrapper over it.
        del self.info.settings.compiler.cppstd

    def validate(self):
        if (str(self.settings.os), str(self.settings.arch)) not in self._extension_platforms:
            raise ConanInvalidConfiguration(
                f"{self.ref} ships prebuilt extensions only for Linux x86_64/armv8, Windows x86/x86_64 and macOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Warnings as errors break the build on compilers newer than upstream tests with.
        flags = os.path.join(self.source_folder, "cmake", "compiler_flags.cmake")
        replace_in_file(self, flags, 'set(CLANG_WARNINGS_AS_ERRORS "-Werror")', "")
        replace_in_file(self, flags, 'set(GNU_WARNINGS_AS_ERRORS "-Werror")', "")
        replace_in_file(self, flags, 'set(MSVC_WARNINGS_AS_ERRORS "/WX")', "")

    def generate(self):
        tc = CMakeToolchain(self)
        # The bundled third-party libraries (libusb, libuvc, live555, libjpeg-turbo,
        # libyuv, spdlog, jsoncpp, tinyxml2, ...) are Orbbec forks built as static
        # libraries into the SDK, whose symbols are hidden; they are not unbundled.
        tc.cache_variables["OB_BUILD_EXAMPLES"] = False
        tc.cache_variables["OB_BUILD_TESTS"] = False
        tc.cache_variables["OB_BUILD_TOOLS"] = False
        tc.cache_variables["OB_BUILD_DOCS"] = False
        tc.cache_variables["OB_INSTALL_EXAMPLES_SOURCE"] = False
        tc.cache_variables["OB_INSTALL_LICENSES"] = True
        tc.cache_variables["OB_BUILD_USB_PAL"] = True
        tc.cache_variables["OB_BUILD_NET_PAL"] = True
        tc.cache_variables["OB_BUILD_GMSL_PAL"] = bool(self.options.get_safe("with_gmsl", False))
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs the third-party licenses into licenses/ already.
        rename(self, os.path.join(self.package_folder, "LICENSE.txt"),
               os.path.join(self.package_folder, "licenses", "LICENSE.txt"))
        # udev rules, their install script and config docs.
        rename(self, os.path.join(self.package_folder, "shared"), os.path.join(self.package_folder, "res"))
        rm(self, "setup.sh", self.package_folder)
        rm(self, "OrbbecSDKConfig.md", os.path.join(self.package_folder, "lib"))
        rm(self, "OrbbecSDKConfig.md", os.path.join(self.package_folder, "bin"))
        # googletest is used only by the tests, which are not built.
        rmdir(self, os.path.join(self.package_folder, "licenses", "googletest"))
        rm(self, "OrbbecSDKConfig*.cmake", os.path.join(self.package_folder, "lib"))
        rm(self, "OrbbecSDKVersion.cmake", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OrbbecSDK")
        self.cpp_info.set_property("cmake_target_name", "ob::OrbbecSDK")
        self.cpp_info.libs = ["OrbbecSDK"]
        self.cpp_info.resdirs = ["res"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread"]
