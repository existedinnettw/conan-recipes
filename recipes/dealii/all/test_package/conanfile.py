from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "test_package.cc"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Let the test source check that the recipe options really reached deal.II's
        # config.h instead of silently staying at configure's defaults.
        options = self.dependencies["dealii"].options
        for macro, option in (
            ("EXPECT_MPI", "with_mpi"),
            ("EXPECT_P4EST", "with_p4est"),
            ("EXPECT_PETSC", "with_petsc"),
            ("EXPECT_METIS", "with_metis"),
            ("EXPECT_LAPACK", "with_lapack"),
            ("EXPECT_ZLIB", "with_zlib"),
            ("EXPECT_COMPLEX_VALUES", "with_complex_values"),
            ("EXPECT_64BIT_INDICES", "int64"),
        ):
            tc.preprocessor_definitions[macro] = int(bool(options.get_safe(option)))
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            exe = self.cpp.build.bindir + "/test_package"
            self.run(exe, env="conanrun")
            if self.dependencies["dealii"].options.with_mpi:
                # --oversubscribe: CI runners may report fewer slots than requested.
                self.run(f"mpiexec --oversubscribe -n 2 {exe}", env="conanrun")
