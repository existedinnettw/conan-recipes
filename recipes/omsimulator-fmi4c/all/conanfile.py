import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir


class OMSimulatorFmi4cConan(ConanFile):
    """OpenModelica's fork of fmi4c, the FMU loading library OMSimulator is built on.

    It keeps fmi4c's pre-1.0 API (one fmiHandle per FMU), which upstream fmi4c 1.x
    replaced with separate FMU and instance handles, so it is packaged under its own name.
    The "miniunz" component holds OMSimulator's modified minizip command line code, which
    both fmi4c and OMSimulator unzip with.
    """

    name = "omsimulator-fmi4c"
    description = "OpenModelica's fork of fmi4c, a C library for loading FMI 1.0/2.0/3.0 FMUs"
    license = ("MIT", "Zlib")
    url = "https://github.com/OpenModelica/OMSimulator-3rdParty"
    homepage = "https://github.com/OpenModelica/OMSimulator-3rdParty/tree/master/fmi4c"
    topics = ("fmi", "fmu", "co-simulation", "model-exchange", "openmodelica")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        # miniunz.c and minizip.c use the POSIX file API unless built with minizip's
        # iowin32, which the minizip package does not provide.
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} is not packaged for Windows")

    def requirements(self):
        # fmi4c.h does not include minizip, but static consumers link it.
        self.requires("minizip/[>=1.2.13 <2]")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "fmi4c"), dst=licenses)
        # miniunz.c and minizip.c are zlib's contrib/minizip, under the zlib license (in
        # their file headers).
        copy(self, "MiniZip64_info.txt", src=os.path.join(self.source_folder, "minizip", "src"), dst=licenses)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "omsimulator-fmi4c")

        miniunz = self.cpp_info.components["miniunz"]
        miniunz.set_property("cmake_target_name", "omsimulator-fmi4c::miniunz")
        miniunz.libs = ["miniunz"]
        miniunz.requires = ["minizip::minizip"]

        fmi4c = self.cpp_info.components["fmi4c"]
        fmi4c.set_property("cmake_target_name", "omsimulator-fmi4c::fmi4c")
        fmi4c.libs = ["fmi4c"]
        fmi4c.requires = ["miniunz"]
        # Upstream's PUBLIC compile definitions.
        fmi4c.defines = ["HAVE_MEMMOVE=1", "EZXML_NOMMAP", "USE_FILE32API"]
        if not self.options.shared:
            fmi4c.defines.append("FMI4C_STATIC")
        if self.settings.os in ("Linux", "FreeBSD"):
            fmi4c.system_libs = ["dl"]
