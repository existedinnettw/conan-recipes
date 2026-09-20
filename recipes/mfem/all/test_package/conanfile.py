from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "test_package.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Hand the recipe options to the test source so it can static_assert that the
        # matching MFEM_USE_* macros were really compiled in. MFEM configures itself
        # through the CMake cache, so an option that fails to reach it stays silently
        # at its upstream default instead of failing the build.
        options = self.dependencies["mfem"].options
        for macro, option in (
            ("EXPECT_MPI", "with_mpi"),
            ("EXPECT_ZLIB", "with_zlib"),
            ("EXPECT_LAPACK", "with_lapack"),
            ("EXPECT_OPENMP", "with_openmp"),
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
