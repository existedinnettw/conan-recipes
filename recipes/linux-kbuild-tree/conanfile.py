import os
import re
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import copy, save


class LinuxKbuildTreeConan(ConanFile):
    name = "linux-kbuild-tree"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "url": ["ANY"],
        "defconfig": ["ANY"],
        "make_modules": [True, False],
    }

    default_options = {
        "url": "https://github.com/torvalds/linux.git",
        "defconfig": "",
        "make_modules": False,
    }

    exports_sources = "configs/*"

    def package_id(self):
        arch = self.conf.get("user.kernel:arch", default=None)
        if arch:
            self.info.conf.define("user.kernel:arch", str(arch))

        cross_compile = self.conf.get("user.kernel:cross_compile", default=None)
        if cross_compile is None:
            cross_compile = self._cross_compile_from_compiler_executables()
        if cross_compile is not None:
            self.info.conf.define("user.kernel:cross_compile", str(cross_compile))

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("linux-kbuild-tree requires a Linux target")

        if not self.version:
            raise ConanInvalidConfiguration(
                "linux-kbuild-tree requires a package version, e.g. "
                "conan create recipes/linux-kbuild-tree --version=6.5.9"
            )

        self._kernel_arch

        if cross_building(self) and self._cross_compile is None:
            raise ConanInvalidConfiguration(
                "Cross-building a kernel tree requires user.kernel:cross_compile "
                "or tools.build:compiler_executables with a GCC-like C compiler"
            )

    def source(self):
        self.run(
            "git clone --depth=1 "
            f"--branch {shlex.quote(self._source_ref)} "
            f"{shlex.quote(str(self.options.url))} linux"
        )

    def build(self):
        linux = os.path.join(self.source_folder, "linux")
        arch = self._kernel_arch
        cross_compile = self._cross_compile or ""
        jobs = self.conf.get("tools.build:jobs", default=None)
        make_jobs = f" -j{jobs}" if jobs else ""

        make_base = (
            f"make -C {shlex.quote(linux)}{make_jobs} "
            f"ARCH={shlex.quote(str(arch))} "
            f"CROSS_COMPILE={shlex.quote(str(cross_compile))}"
        )

        self._install_config(linux, make_base)

        self.run(f"{make_base} olddefconfig prepare modules_prepare")

        if self.options.make_modules:
            # Required when CONFIG_MODVERSIONS=y and the target kernel exports
            # symbols that are not available from a vendor-provided Module.symvers.
            self.run(f"{make_base} modules")

        kernelrelease = self._capture(f"{make_base} kernelrelease")
        compiler = self._capture(f"{self._cross_gcc} --version").splitlines()[0]
        git_commit = self._capture(f"git -C {shlex.quote(linux)} rev-parse HEAD")

        save(
            self,
            os.path.join(self.build_folder, "kbuild-tree-info.txt"),
            "\n".join(
                [
                    f"url={self.options.url}",
                    f"ref={self.version}",
                    f"git_commit={git_commit}",
                    f"kernelrelease={kernelrelease}",
                    f"arch={arch}",
                    f"cross_compile={cross_compile}",
                    f"compiler={compiler}",
                    f"make_modules={self.options.make_modules}",
                    "",
                ]
            ),
        )

    def package(self):
        linux = os.path.join(self.source_folder, "linux")

        # External module builds need source files, generated headers, scripts,
        # .config, and often Module.symvers. Packaging the whole prepared tree is
        # intentionally conservative and can be optimized after the flow is stable.
        copy(self, "*", src=linux, dst=self.package_folder, excludes=(".git", ".git/*"))
        copy(self, ".config", src=linux, dst=self.package_folder, keep_path=False)
        copy(
            self,
            "kbuild-tree-info.txt",
            src=self.build_folder,
            dst=self.package_folder,
            keep_path=False,
        )

    def package_info(self):
        self.conf_info.define("user.kernel:kernel_dir", self.package_folder)
        self.conf_info.define("user.kernel:arch", self._kernel_arch)
        self.conf_info.define("user.kernel:cross_compile", self._cross_compile or "")

    @property
    def _kernel_arch(self):
        arch = self.conf.get("user.kernel:arch", default=None)
        if arch:
            return str(arch)

        arch = str(self.settings.arch)
        arch_map = {
            "x86": "x86",
            "x86_64": "x86",
            "armv5el": "arm",
            "armv5hf": "arm",
            "armv6": "arm",
            "armv7": "arm",
            "armv7hf": "arm",
            "armv8": "arm64",
            "armv8_32": "arm",
            "armv8.3": "arm64",
            "armv8.5": "arm64",
            "armv8.6": "arm64",
            "armv8.7": "arm64",
            "armv8.8": "arm64",
            "armv8.9": "arm64",
            "ppc32": "powerpc",
            "ppc64": "powerpc",
            "ppc64le": "powerpc",
            "riscv32": "riscv",
            "riscv64": "riscv",
            "s390": "s390",
            "s390x": "s390",
            "sparc": "sparc",
            "sparcv9": "sparc",
            "mips": "mips",
            "mips64": "mips",
        }
        if arch not in arch_map:
            raise ConanInvalidConfiguration(
                f"Cannot derive Linux ARCH from settings.arch={arch!r}; "
                "set user.kernel:arch explicitly"
            )
        return arch_map[arch]

    @property
    def _cross_compile(self):
        cross_compile = self.conf.get("user.kernel:cross_compile", default=None)
        if cross_compile is not None:
            return str(cross_compile)

        if not cross_building(self):
            return ""

        c_compiler = self._compiler_executable("c")
        if not c_compiler:
            return None

        return self._cross_compile_from_executable(c_compiler)

    def _cross_compile_from_compiler_executables(self):
        c_compiler = self._compiler_executable("c")
        if not c_compiler:
            return None
        return self._cross_compile_from_executable(c_compiler)

    def _cross_compile_from_executable(self, c_compiler):
        executable = os.path.basename(c_compiler)
        match = re.match(r"^(.+?)(?:gcc|cc)(?:-\d+(?:\.\d+)*)?$", executable)
        if not match:
            return None
        return match.group(1)

    @property
    def _cross_gcc(self):
        cross_compile = self._cross_compile or ""
        return shlex.quote(f"{cross_compile}gcc")

    def _compiler_executable(self, language):
        executables = self.conf.get("tools.build:compiler_executables", default={})
        if not executables:
            return None
        if hasattr(executables, "get"):
            return executables.get(language)
        return None

    def _install_config(self, linux, make_base):
        defconfig = str(self.options.defconfig)
        if not defconfig:
            if not os.path.exists(os.path.join(linux, ".config")):
                raise ConanInvalidConfiguration(
                    "Missing kernel config: set linux-kbuild-tree/*:defconfig "
                    "or provide a source tree with .config"
                )
            return

        exported_config = os.path.join(self.source_folder, "configs", defconfig)
        if os.path.isfile(exported_config):
            copy(
                self,
                defconfig,
                src=os.path.dirname(exported_config),
                dst=linux,
                keep_path=False,
            )
            os.replace(os.path.join(linux, defconfig), os.path.join(linux, ".config"))
            return

        self.run(f"{make_base} {shlex.quote(defconfig)}")

    def _capture(self, command):
        output = subprocess.check_output(
            command,
            shell=True,
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
        if not output:
            raise ConanInvalidConfiguration(f"Command produced no output: {command}")
        return output
