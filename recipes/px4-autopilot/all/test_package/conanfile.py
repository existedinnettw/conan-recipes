import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        px4 = self.dependencies[self.tested_reference_str.split("/")[0]]
        rootfs = os.path.join(px4.package_folder, "etc")
        assert os.path.isfile(os.path.join(rootfs, "init.d-posix", "rcS")), rootfs
        # `px4 -h` prints the daemon/client usage and exits 0.
        self.run("px4 -h", env="conanrun")
