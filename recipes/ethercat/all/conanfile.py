from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os


class EthercatConan(ConanFile):
    name = "ethercat"
    license = "LGPL-2.1-only"
    author = "Florian Pose <fp@igh.de>"
    url = "https://gitlab.com/etherlab.org/ethercat"
    description = "IgH EtherCAT Master userspace client library"
    topics = ("ethercat", "industrial", "automation", "fieldbus", "realtime")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "max_num_devices": ["ANY"],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "max_num_devices": 1,
    }

    exports_sources = (
        "CMakeLists.txt",
        "test_package/CMakeLists.txt",
        "test_package/conanfile.py",
        "test_package/test_package.c",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("IgH EtherCAT Master is only supported on Linux")

        try:
            max_devices = int(str(self.options.max_num_devices))
        except ValueError as exc:
            raise ConanInvalidConfiguration("max_num_devices must be an integer") from exc

        if max_devices < 1:
            raise ConanInvalidConfiguration("max_num_devices must be >= 1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["EC_MAX_NUM_DEVICES"] = str(self.options.max_num_devices)
        tc.variables["ETHERCAT_VERSION"] = str(self.version)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ethercat"]
        self.cpp_info.set_property("cmake_file_name", "ethercat")
        self.cpp_info.set_property("cmake_target_name", "EtherLab::ethercat")
        self.cpp_info.set_property("pkg_config_name", "libethercat")
        self.cpp_info.system_libs = ["rt", "pthread"]
