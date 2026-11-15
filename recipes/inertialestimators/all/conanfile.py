import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class InertialEstimatorsConan(ConanFile):
    name = "inertialestimators"
    description = "C++ inertial attitude and heading estimators, including Mahony, Madgwick and EKF filters"
    license = "MIT", "BSD-3-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/Tellicious/InertialEstimators"
    topics = ("imu", "ahrs", "sensor-fusion", "mahony", "madgwick")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("matlib/cci.20231209", transitive_headers=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Retain the BSD notices of the PX4-derived estimators in binary packages.
        copy(self, "AHRS_Attitude_*.h", os.path.join(self.source_folder, "Cpp", "inc"),
             os.path.join(self.package_folder, "licenses", "px4"))
        CMake(self).install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "inertialestimators")
        self.cpp_info.set_property("cmake_target_name", "inertialestimators::inertialestimators")
        self.cpp_info.libs = ["inertialestimators"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
