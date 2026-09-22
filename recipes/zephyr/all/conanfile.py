import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, rmdir, save


class ZephyrConan(ConanFile):
    """Zephyr RTOS west workspace, packaged as Conan infrastructure.

    This recipe implements the "Conan outside" architecture: Conan owns the
    package/dependency/environment graph and pins the Zephyr platform revision,
    while ``west build`` (and sysbuild) untouched underneath owns the firmware
    image graph. The package is the full west workspace (zephyr + every
    west-managed module such as HALs, CMSIS, MCUboot), so nothing about
    Zephyr's module graph has to be duplicated in Conan.

    The Zephyr SDK is intentionally *not* part of this package. Provide it via
    the ``zephyr-sdk`` recipe (``tool_requires``) or from the environment via
    ``ZEPHYR_SDK_INSTALL_DIR`` / ``ZEPHYR_TOOLCHAIN_VARIANT``.

    Consume it as an ordinary requirement (it ends up compiled into the firmware)::

        def requirements(self):
            self.requires("zephyr/4.4.0")

    which exports ``ZEPHYR_BASE`` into the build environment, so an ordinary
    ``west build -b <board> <app>`` works from any directory.
    """

    name = "zephyr"
    license = "Apache-2.0"
    url = "https://github.com/zephyrproject-rtos/zephyr"
    homepage = "https://www.zephyrproject.org"
    description = "Zephyr RTOS source tree together with its west-managed modules (a complete west workspace)"
    topics = ("zephyr", "rtos", "embedded", "west", "firmware")
    package_type = "unknown"

    options = {
        # Comma-separated west project names to fetch (``west update <names>``).
        # Empty means every project active in Zephyr's manifest (all HALs, ...).
        "projects": ["ANY"],
        # Comma-separated west group-filter, e.g. "-hal,+hal_stm32".
        "group_filter": ["ANY"],
        # Shallow clone every project (``west update --narrow -o=--depth=1``).
        "narrow": [True, False],
        # Keep the .git directories. They are large and unused by ``west build``;
        # enable only if you need ``west update`` or git metadata in the package.
        "keep_git": [True, False],
    }
    default_options = {
        "projects": "",
        "group_filter": "",
        "narrow": True,
        "keep_git": False,
    }

    no_copy_source = True

    @property
    def _workspace(self):
        return os.path.join(self.source_folder, "workspace")

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def validate(self):
        if not self.version:
            raise ConanInvalidConfiguration(
                "zephyr requires a version, e.g. conan create recipes/zephyr/all --version=4.3.0"
            )
        if str(self.version) not in self.conan_data.get("sources", {}):
            raise ConanInvalidConfiguration(
                f"zephyr/{self.version} is not listed in conandata.yml"
            )

    def validate_build(self):
        missing = [tool for tool in ("west", "git") if shutil.which(tool) is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Building zephyr/{self.version} needs {', '.join(missing)} on PATH. "
                "Install them first, e.g. `pip install west` in a virtualenv on PATH."
            )

    def source(self):
        # Only the manifest repository is fetched here; the module set depends on
        # options and is therefore resolved in build().
        src = self.conan_data["sources"][str(self.version)]
        url = src["url"]
        revision = src["revision"]
        # The manifest repo is always shallow; the tag is what pins the platform.
        self.run(
            f"git clone --branch {shlex.quote(revision)} --depth=1 {shlex.quote(url)} "
            f"{shlex.quote(os.path.join(self._workspace, 'zephyr'))}"
        )
        self.run(
            f"west init -l {shlex.quote(os.path.join(self._workspace, 'zephyr'))}",
            cwd=self._workspace,
        )

    def build(self):
        # source() is shared between configurations (no_copy_source) and must not be
        # mutated, so replay the workspace into the build folder before west update.
        workspace = os.path.join(self.build_folder, "workspace")
        if os.path.isdir(workspace):
            rmdir(self, workspace)
        shutil.copytree(self._workspace, workspace, symlinks=True)

        group_filter = str(self.options.group_filter)
        if group_filter:
            self.run(
                f"west config manifest.group-filter {shlex.quote(group_filter)}",
                cwd=workspace,
            )

        update = "west update"
        if self.options.narrow:
            update += " --narrow -o=--depth=1"
        projects = [p.strip() for p in str(self.options.projects).split(",") if p.strip()]
        if projects:
            update += " " + " ".join(shlex.quote(p) for p in projects)
        self.run(update, cwd=workspace)

        # Zephyr's version.cmake and west use these; record them before .git goes away.
        head = self._capture("git rev-parse HEAD", cwd=os.path.join(workspace, "zephyr"))
        save(
            self,
            os.path.join(self.build_folder, "zephyr-workspace-info.txt"),
            "\n".join(
                [
                    f"version={self.version}",
                    f"revision={self.conan_data['sources'][str(self.version)]['revision']}",
                    f"sha={head}",
                    f"projects={','.join(projects) if projects else '<all>'}",
                    f"group_filter={group_filter}",
                    f"narrow={self.options.narrow}",
                    f"keep_git={self.options.keep_git}",
                    "",
                ]
            ),
        )

    def package(self):
        workspace = os.path.join(self.build_folder, "workspace")
        excludes = () if self.options.keep_git else (".git", "*/.git", "*/.git/*")
        copy(self, "*", src=workspace, dst=self.package_folder, excludes=excludes)
        # ``copy`` skips dotfiles-only trees inconsistently; make sure west's
        # workspace marker and manifest config are present.
        copy(self, "*", src=os.path.join(workspace, ".west"), dst=os.path.join(self.package_folder, ".west"))
        if not self.options.keep_git:
            for root, dirs, _ in os.walk(self.package_folder):
                if ".git" in dirs:
                    rmdir(self, os.path.join(root, ".git"))
                    dirs.remove(".git")
        copy(
            self,
            "LICENSE",
            src=os.path.join(workspace, "zephyr"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(self, "zephyr-workspace-info.txt", src=self.build_folder, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        # This package is not a CMake library. Without this, CMakeDeps would
        # generate a zephyr-config.cmake that shadows Zephyr's own
        # ``find_package(Zephyr)`` package config once the generators folder
        # is on CMAKE_PREFIX_PATH (which is how consumers expose spdlog & co).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("pkg_config_name", "none")

        zephyr_base = os.path.join(self.package_folder, "zephyr")
        # Lets both west (workspace discovery falls back to ZEPHYR_BASE) and
        # ``find_package(Zephyr HINTS $ENV{ZEPHYR_BASE})`` locate the tree.
        self.buildenv_info.define_path("ZEPHYR_BASE", zephyr_base)
        self.runenv_info.define_path("ZEPHYR_BASE", zephyr_base)
        self.conf_info.define("user.zephyr:base", zephyr_base)
        self.conf_info.define("user.zephyr:workspace", self.package_folder)

    def _capture(self, command, cwd):
        return subprocess.check_output(command, shell=True, cwd=cwd, text=True).strip()
