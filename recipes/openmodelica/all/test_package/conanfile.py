import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    """Exports a Modelica model with openmodelica_add_fmu() and co-simulates the FMU."""

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.build_context_activated = ["openmodelica"]
        deps.build_context_build_modules = ["openmodelica"]
        deps.generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            fmu_dir = os.path.join(self.build_folder, "Decay")
            self.run(f'{os.path.join(self.cpp.build.bindir, "test_package")} "{fmu_dir}"', env="conanrun")
