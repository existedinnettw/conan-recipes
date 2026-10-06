import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"


class ASVSimConan(ConanFile):
    name = "asvsim"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/BavoLesy/ASVSim"
    description = ("AirLib and MavLinkCom from ASVSim (IDLab-ASVSim), the Cosys-AirSim fork that "
                   "simulates surface vessels: the C++ client API to drive a running simulation")
    topics = ("airsim", "simulation", "unreal-engine", "vessel", "marine", "robotics", "mavlink", "rpc")
    package_type = "library"
    # Only the C++ libraries are packaged; the Unreal plugin is built by Unreal Engine.
    # It is a fork of cosys-airsim with the same library names, so the two cannot be linked
    # into one program.

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    exports_sources = "CMakeLists.txt"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Upstream bundles forks of rpclib 2.3.1 and Eigen 3.4.1; AirLib uses neither
        # fork's additions (rpc::server::unbind, warning fixes).
        self.requires("rpclib/2.3.0", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/3.4.1", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 17)
        # The libraries have no export macros, so a DLL would export nothing.
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} can only be built as a static library on Windows")

    def source(self):
        # The archive is ~280 MB, almost all Unreal content and documentation.
        get(self, **self.conan_data["sources"][self.version], strip_root=True,
            excludes=["*/docs/*", "*/Unreal/*", "*/Matlab/*", "*/PythonClient/*", "*/LogViewer/*"])
        copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream has no CMake package; headers are included the way the Unreal plugin does,
        # e.g. "vehicles/multirotor/api/MultirotorRpcLibClient.hpp".
        self.cpp_info.set_property("cmake_file_name", "asvsim")

        mavlinkcom = self.cpp_info.components["mavlinkcom"]
        mavlinkcom.set_property("cmake_target_name", "asvsim::MavLinkCom")
        mavlinkcom.libs = ["MavLinkCom"]
        mavlinkcom.includedirs = [os.path.join("include", "MavLinkCom")]
        if self.settings.os in ("Linux", "FreeBSD"):
            mavlinkcom.system_libs = ["pthread"]
        elif self.settings.os == "Windows":
            mavlinkcom.system_libs = ["ws2_32", "wbemuuid", "ole32", "oleaut32", "setupapi", "cfgmgr32"]

        airlib = self.cpp_info.components["airlib"]
        airlib.set_property("cmake_target_name", "asvsim::AirLib")
        airlib.libs = ["AirLib"]
        airlib.includedirs = [os.path.join("include", "AirLib")]
        airlib.requires = ["mavlinkcom", "rpclib::rpclib", "eigen::eigen"]
