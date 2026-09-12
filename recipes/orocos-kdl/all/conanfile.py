import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.microsoft import is_msvc


class OrocosKdlConan(ConanFile):
    name = "orocos-kdl"
    description = "Orocos Kinematics and Dynamics C++ library"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/orocos/orocos_kinematics_dynamics"
    homepage = "https://www.orocos.org/kdl"
    topics = ("robotics", "kinematics", "dynamics", "motion")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "use_new_tree_interface": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "use_new_tree_interface": False,
    }

    @property
    def _subfolder(self):
        # The repository is a multi-package ROS-style repo; only orocos_kdl is built here.
        return "orocos_kdl"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # KDL exposes Eigen types in its public headers.
        self.requires("eigen/[>=3.3 <4]", transitive_headers=True)
        if self.options.use_new_tree_interface:
            # The new Tree interface uses boost::shared_ptr in public headers.
            self.requires("boost/[>=1.71 <2]", transitive_headers=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 14)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["KDL_USE_NEW_TREE_INTERFACE"] = bool(self.options.use_new_tree_interface)
        tc.variables["ENABLE_TESTS"] = False
        tc.variables["ENABLE_EXAMPLES"] = False
        tc.variables["BUILD_MODELS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=self._subfolder)
        cmake.build()

    def package(self):
        copy(
            self,
            "COPYING",
            src=os.path.join(self.source_folder, self._subfolder),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        # Upstream ships its own CMake config and .pc files, which hard-code build
        # machine paths. CMakeDeps/PkgConfigDeps generate correct ones instead.
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "orocos_kdl")
        self.cpp_info.set_property("cmake_target_name", "orocos-kdl::orocos-kdl")
        # Consumers written against a system/ROS install link the bare target.
        self.cpp_info.set_property("cmake_target_aliases", ["orocos-kdl"])
        self.cpp_info.set_property("pkg_config_name", "orocos-kdl")

        suffix = "d" if is_msvc(self) and self.settings.build_type == "Debug" else ""
        self.cpp_info.libs = [f"orocos-kdl{suffix}"]

        if self.settings.os == "Windows" and self.options.shared:
            self.cpp_info.defines.append("OROCOS_KDL_USE_SHARED")
