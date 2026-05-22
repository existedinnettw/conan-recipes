import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "Makefile", "test_kbuild_module.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def build(self):
        kernel_tree = self.dependencies["linux-kbuild-tree"].package_folder
        module_dir = os.path.join(self.build_folder, "module")
        copy(self, "*", src=self.source_folder, dst=module_dir)

        tree_info = self._read_tree_info(kernel_tree)
        arch = tree_info.get("arch", "")
        cross_compile = tree_info.get("cross_compile", "")
        jobs = self.conf.get("tools.build:jobs", default=None)
        make_jobs = f" -j{jobs}" if jobs else ""

        command = (
            f"make --no-print-directory -C {shlex.quote(kernel_tree)}{make_jobs} "
            f"M={shlex.quote(module_dir)} "
            f"ARCH={shlex.quote(arch)} "
            f"CROSS_COMPILE={shlex.quote(cross_compile)} "
            "KBUILD_MODPOST_WARN=1 "
            "modules"
        )
        self.run(command)

    def test(self):
        module_path = os.path.join(self.build_folder, "module", "test_kbuild_module.ko")
        if not os.path.isfile(module_path):
            raise ConanException(f"Kernel module was not built: {module_path}")

    def _read_tree_info(self, kernel_tree):
        path = os.path.join(kernel_tree, "kbuild-tree-info.txt")
        if not os.path.isfile(path):
            raise ConanException(f"Missing linux-kbuild-tree metadata: {path}")

        result = {}
        with open(path, encoding="utf-8") as tree_info:
            for line in tree_info:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                result[key] = value
        return result
