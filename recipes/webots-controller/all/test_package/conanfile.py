from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class TestPackageConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # check if RUNTIME_DEPENDENCY_SET work
        cmake = CMake(self)
        cmake.install()
        if can_run(self):
            exe = os.path.join(self.source_folder, "test_package")
            self.run(exe, env="conanrun")
            exe = os.path.join(self.source_folder, "test_package_c")
            self.run(exe, env="conanrun")
