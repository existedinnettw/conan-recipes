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
        # Let the test source check that the recipe options really reached petscconf.h
        # instead of silently staying at configure's defaults.
        options = self.dependencies["petsc"].options
        for macro, option in (
            ("EXPECT_MPI", "with_mpi"),
            ("EXPECT_HYPRE", "with_hypre"),
            ("EXPECT_METIS", "with_metis"),
            ("EXPECT_PARMETIS", "with_parmetis"),
            ("EXPECT_PTSCOTCH", "with_ptscotch"),
            ("EXPECT_SUPERLU_DIST", "with_superlu_dist"),
            ("EXPECT_HDF5", "with_hdf5"),
            ("EXPECT_ZLIB", "with_zlib"),
            ("EXPECT_INT64", "int64"),
        ):
            tc.preprocessor_definitions[macro] = int(bool(options.get_safe(option)))
        tc.preprocessor_definitions["EXPECT_COMPLEX"] = int(options.scalar_type == "complex")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            exe = self.cpp.build.bindir + "/test_package"
            self.run(exe, env="conanrun")
            if self.dependencies["petsc"].options.with_mpi:
                # --oversubscribe: CI runners may report fewer slots than requested.
                self.run(f"mpiexec --oversubscribe -n 2 {exe}", env="conanrun")
