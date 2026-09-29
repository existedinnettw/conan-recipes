import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class MalibConan(ConanFile):
    name = "malib"
    description = (
        "MADOCA-PPP Library: JAXA's RTKLIB fork for precise point positioning with "
        "QZSS MADOCA-PPP (L6E) corrections, with the rtkrcv and rnx2rtkp tools"
    )
    license = "BSD-2-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/JAXA-SNU/MALIB"
    topics = ("gnss", "gps", "qzss", "madoca", "ppp", "ppp-ar", "rtklib", "positioning")
    package_type = "library"
    # Installs RTKLIB's rtklib.h and API with MALIB's extensions, so it cannot
    # share a graph with rtklib (Conan Center) or rtklib-explorer.
    provides = "rtklib"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # Named as in Conan Center's rtklib recipe, so profiles fit both. NFREQ
        # and NEXOBS size the observation arrays in rtklib.h; the defaults are
        # the ones of upstream's makefiles.
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
        "num_frequencies": 5,
        "num_ext_obs_codes": 5,
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

    def validate(self):
        # Upstream builds with gcc makefiles only; its Windows release links the
        # MALIB engine into RTKLIB's C++Builder GUI instead. The headers also lack
        # RTKLIB's EXPORT macros, so a DLL would export nothing.
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} supports POSIX systems only")

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
        tc.cache_variables["MALIB_PUBLIC_DEFINES"] = ";".join(self._public_defines)
        tc.cache_variables["MALIB_BUILD_TOOLS"] = bool(self.options.with_tools)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "malib")
        self.cpp_info.set_property("cmake_target_name", "malib::malib")
        self.cpp_info.libs = ["malib"]
        self.cpp_info.defines = list(self._public_defines)
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "pthread"]
