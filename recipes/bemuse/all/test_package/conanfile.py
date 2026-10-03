import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import load, mkdir, save


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        self.run(os.path.join(self.cpp.build.bindir, "test_package"), cwd=self.build_folder, env="conanrun")

        # The command-line program reads its parameters from Input/*.bemin and writes
        # Output/<prefix>.* , both relative to the working directory.
        workdir = os.path.join(self.build_folder, "cli")
        mkdir(self, os.path.join(workdir, "Input"))
        inputs = {
            # Semi-axes a, b, c and depth of the centre.
            "Dimensions.bemin": "BDRY 1.0\nBDRY 1.0\nBDRY 1.0\nBDRY 3.0\n",
            # Azimuthal and zenith panels.
            "Discretisation.bemin": "BDRY 12\nBDRY 8\n",
            "Frequencies.bemin": "0.5\n1.0\n",
            "WaveAngles.bemin": "0.0\n",
            "SolverParams.bemin": "FALSE Irregular\nINF Depth\n36 Kochin\n1025 Density\n9.81 Acceleration\n",
        }
        for name, content in inputs.items():
            save(self, os.path.join(workdir, "Input", name), content)
        self.run("BEMUse Templates", env="conanrun")
        self.run("BEMUse Ellipsoid sphere -t2", cwd=workdir, env="conanrun")
        radiation = load(self, os.path.join(workdir, "Output", "sphere.1")).strip().splitlines()
        if not radiation:
            raise RuntimeError("BEMUse wrote no radiation coefficients to Output/sphere.1")
        self.output.info(f"Output/sphere.1: {len(radiation)} lines")
