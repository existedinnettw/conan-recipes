import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "app/*", "case/*"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        # The usual OpenFOAM way: wmake, with the environment the package provides.
        app = os.path.join(self.build_folder, "app")
        shutil.rmtree(app, ignore_errors=True)
        shutil.copytree(os.path.join(self.source_folder, "app"), app)
        self.run(f"bash -c 'FOAM_USER_APPBIN=\"{self.build_folder}\" wmake'", cwd=app)

        # And through CMake, with the targets from package_info.
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        case = os.path.join(self.build_folder, "case")
        shutil.rmtree(case, ignore_errors=True)
        shutil.copytree(os.path.join(self.source_folder, "case"), case)

        def run(command):
            self.run(f"{command} -case {case}", env="conanrun")

        run("blockMesh")
        run("checkMesh")
        # scotch decomposition, then a parallel run through Pstream and Open MPI.
        run("decomposePar")
        wmake_app = os.path.join(self.build_folder, "test_package_wmake")
        run(f"mpirun --oversubscribe -np 2 {wmake_app} -parallel")
        run(os.path.join(self.cpp.build.bindir, "test_package_cmake"))
