import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy


class TestPackageConan(ConanFile):
    test_type = "explicit"
    python_requires = "tested_reference_str"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "Makefile", "test_kbuild_module.c"

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def build(self):
        linux_kbuild_tree = self.python_requires["linux-kbuild-tree"].module
        tree_info = linux_kbuild_tree.prepare(
            self,
            output=os.path.join(self.build_folder, "linux-kbuild-tree"),
        )

        kernel_tree = tree_info["path"]
        module_dir = os.path.join(self.build_folder, "module")
        copy(self, "*", src=self.source_folder, dst=module_dir)

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
