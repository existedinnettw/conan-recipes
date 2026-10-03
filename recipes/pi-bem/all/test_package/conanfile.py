import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import save
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return
        # Upstream's default 2D problem, which reads its mesh from ../grids/circle.inp.
        grids = os.path.join(self.dependencies["pi-bem"].package_folder, "share", "pi-bem", "grids")
        shutil.copytree(grids, os.path.join(self.build_folder, "grids"), dirs_exist_ok=True)
        run = os.path.join(self.build_folder, "run")
        # An empty parameter file: all defaults.
        save(self, os.path.join(run, "parameters_bem_2.prm"), "")
        self.run("bem_fma_2d", env="conanrun", cwd=run)
        assert os.path.isfile(os.path.join(run, "result_scalar_results.vtu"))
