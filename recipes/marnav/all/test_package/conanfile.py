import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindir, "test_package"), env="conanrun")
            marnav = self.dependencies[self.tested_reference_str]
            if marnav.options.with_tools:
                # A static library package is not a run requirement, so its bin
                # folder is not on PATH.
                self.run(os.path.join(marnav.package_folder, "bin", "nmeatool") + " --version",
                         env="conanrun")
