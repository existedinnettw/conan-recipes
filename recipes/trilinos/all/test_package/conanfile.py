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
            exe = self.cpp.build.bindir + "/test_package"
            self.run(exe, env="conanrun")
            if self.dependencies["trilinos"].options.with_mpi:
                # --oversubscribe: CI runners may report fewer slots than requested.
                self.run(f"mpiexec --oversubscribe -n 2 {exe}", env="conanrun")
