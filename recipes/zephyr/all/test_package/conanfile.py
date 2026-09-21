import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    """Builds Zephyr's hello_world sample for native_sim with plain ``west build``.

    This mirrors the intended consumer pattern: Conan only provides the pinned
    workspace via ZEPHYR_BASE; west/sysbuild own the firmware build.
    """

    test_type = "explicit"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    @property
    def _zephyr_base(self):
        return self.dependencies["zephyr"].conf_info.get("user.zephyr:base")

    @property
    def _build_dir(self):
        return os.path.join(self.build_folder, "hello_world")

    def build(self):
        info = os.path.join(self.dependencies["zephyr"].package_folder, "zephyr-workspace-info.txt")
        if not os.path.isfile(info):
            raise ConanException(f"Missing workspace metadata: {info}")

        # ``west list`` must resolve the manifest and modules from ZEPHYR_BASE alone
        # (the test package is not inside the workspace).
        self.run("west list")

        app = os.path.join(self._zephyr_base, "samples", "hello_world")
        self.run(f"west build --pristine=always -b native_sim/native/64 -d {self._build_dir} {app}")

    def test(self):
        exe = os.path.join(self._build_dir, "zephyr", "zephyr.exe")
        if not os.path.isfile(exe):
            raise ConanException(f"west build did not produce {exe}")
        if can_run(self):
            self.run(f"{exe} -stop_at=1")
