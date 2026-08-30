import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "CO_driver_target.h", "test_package.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("edssharp/4.2.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tool = self.dependencies.build["edssharp"]
        toolchain = CMakeToolchain(self)
        toolchain.variables["EDSSharp_EXECUTABLE"] = os.path.join(
            tool.package_folder, "bin", "EDSSharp"
        )
        canopennode = self.dependencies["canopennode"]
        toolchain.variables["TEST_OD_INPUT"] = os.path.join(
            canopennode.package_folder, "res", "DS301_profile.eds"
        )
        toolchain.generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(self.cpp.build.bindir + "/test_package", env="conanrun")
