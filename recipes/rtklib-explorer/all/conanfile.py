import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class RtklibExplorerConan(ConanFile):
    name = "rtklib-explorer"
    description = (
        "rtklibexplorer's RTKLIB fork (demo5): GNSS standard and precise positioning "
        "(RTK, PPP) library and console tools, tuned for low cost receivers"
    )
    license = "BSD-2-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/rtklibexplorer/RTKLIB"
    topics = ("gnss", "gps", "rtk", "ppp", "rinex", "rtcm", "positioning")
    package_type = "library"
    # Conan Center's rtklib packages the original tomojitakasu/RTKLIB, whose API
    # this fork has diverged from; both install rtklib.h and librtklib.
    provides = "rtklib"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # Named as in Conan Center's rtklib recipe, so profiles fit both. NFREQ
        # and NEXOBS size the observation arrays in rtklib.h; the defaults are
        # the ones of upstream's CMake and Qt builds.
        "trace": [True, False],
        "enable_glonass": [True, False],
        "enable_qzss": [True, False],
        "enable_galileo": [True, False],
        "enable_beidou": [True, False],
        "enable_irnss": [True, False],
        "num_frequencies": [1, 2, 3, 4, 5, 6],
        "num_ext_obs_codes": [0, 1, 2, 3, 4, 5, 6],
        "with_tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "trace": True,
        "enable_glonass": True,
        "enable_qzss": True,
        "enable_galileo": True,
        "enable_beidou": True,
        "enable_irnss": True,
        "num_frequencies": 3,
        "num_ext_obs_codes": 3,
        "with_tools": True,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _public_defines(self):
        # These size the structs in rtklib.h and switch its trace macros, so every
        # consumer has to see the same values as the library.
        flags = {
            "ENAGLO": self.options.enable_glonass,
            "ENAQZS": self.options.enable_qzss,
            "ENAGAL": self.options.enable_galileo,
            "ENACMP": self.options.enable_beidou,
            "ENAIRN": self.options.enable_irnss,
            "TRACE": self.options.trace,
        }
        return [name for name, enabled in flags.items() if enabled] + [
            f"NFREQ={self.options.num_frequencies}",
            f"NEXOBS={self.options.num_ext_obs_codes}",
        ]

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["RTKLIB_PUBLIC_DEFINES"] = ";".join(self._public_defines)
        tc.cache_variables["RTKLIB_BUILD_TOOLS"] = bool(self.options.with_tools)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "license.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Conan Center's rtklib names, so CMake consumers can switch packages.
        self.cpp_info.set_property("cmake_file_name", "rtklib")
        self.cpp_info.set_property("cmake_target_name", "rtklib::rtklib")
        self.cpp_info.libs = ["rtklib"]
        self.cpp_info.defines = list(self._public_defines)
        if self.settings.os == "Windows":
            self.cpp_info.defines.append("WIN32")
            if self.settings.compiler == "msvc" and not self.options.shared:
                self.cpp_info.defines.append("WIN_STATIC")
            self.cpp_info.system_libs = ["ws2_32", "winmm"]
        elif self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "pthread"]
