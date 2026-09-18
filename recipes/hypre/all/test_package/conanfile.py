from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "test_package.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Let the test source static_assert that the recipe options really reached
        # hypre's configuration header instead of silently staying at their defaults.
        options = self.dependencies["hypre"].options
        for macro, option in (
            ("EXPECT_MPI", "with_mpi"),
            ("EXPECT_BIGINT", "bigint"),
        ):
            tc.preprocessor_definitions[macro] = int(bool(getattr(options, option)))
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(self.cpp.build.bindir + "/test_package", env="conanrun")
