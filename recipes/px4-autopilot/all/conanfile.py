import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy
from conan.tools.scm import Git


class Px4AutopilotConan(ConanFile):
    name = "px4-autopilot"
    license = "BSD-3-Clause"
    url = "https://github.com/PX4/PX4-Autopilot"
    homepage = "https://px4.io"
    description = (
        "PX4 Autopilot flight control software built for POSIX "
        "software-in-the-loop (SITL) simulation"
    )
    topics = ("px4", "autopilot", "drone", "mavlink", "sitl", "simulation")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        # Any POSIX board config from boards/px4/sitl (e.g. px4_sitl_default,
        # px4_sitl_replay, px4_sitl_test).
        "config": ["ANY"],
    }
    default_options = {
        "config": "px4_sitl_default",
    }

    # Submodule trees that SITL never touches: the NuttX RTOS, hardware board
    # SDKs, third-party simulator bridges, and fuzzing corpora.
    _skipped_submodule_prefixes = (
        "platforms/nuttx/",
        "boards/",
        "Tools/simulation/",
        "test/",
    )

    # Subset of Tools/setup/requirements.txt actually imported by the build's
    # code generators (uORB messages, parameters, airframes, kconfig, events).
    _python_requirements = (
        "cerberus",
        "empy>=3.3,<4",
        "future",
        "jinja2>=2.8",
        "jsonschema",
        "kconfiglib",
        "lxml",
        "numpy>=1.13",
        "packaging",
        "pyros-genmsg",
        "pyserial",
        "pyyaml",
        "toml>=0.9",
    )

    @property
    def _venv_dir(self):
        return os.path.join(self.build_folder, "python-venv")

    @property
    def _venv_python(self):
        if self.settings_build.os == "Windows":
            return os.path.join(self._venv_dir, "Scripts", "python.exe")
        return os.path.join(self._venv_dir, "bin", "python3")

    def validate(self):
        if self.settings.os not in ("Linux", "Macos"):
            raise ConanInvalidConfiguration(
                "PX4 SITL only supports POSIX hosts (Linux, macOS)"
            )
        if not str(self.options.config).startswith("px4_sitl_"):
            raise ConanInvalidConfiguration(
                "This recipe only builds POSIX SITL configs (px4_sitl_*); "
                f"got '{self.options.config}'"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        source_data = self.conan_data["sources"][str(self.version)]
        git = Git(self)
        # PX4 derives its firmware version from `git describe`, so the tag must
        # stay reachable in the checkout. A shallow clone on the tag suffices.
        git.clone(
            url=source_data["git_url"],
            target=".",
            args=["--depth", "1", "--branch", source_data["ref"]],
        )
        paths = git.run("config --file .gitmodules --get-regexp path").splitlines()
        submodules = [
            line.split()[1]
            for line in paths
            if not line.split()[1].startswith(self._skipped_submodule_prefixes)
        ]
        git.run(
            "submodule update --init --recursive --depth 1 --jobs 8 -- "
            + " ".join(submodules)
        )

    def generate(self):
        # PX4 code generators need several Python packages. Keep them in a
        # venv private to this build so the host interpreter stays untouched.
        self.run(f'"{sys.executable}" -m venv "{self._venv_dir}"')
        self.run(
            f'"{self._venv_python}" -m pip install --quiet --upgrade pip '
            + " ".join(f'"{req}"' for req in self._python_requirements)
        )

        tc = CMakeToolchain(self)
        tc.cache_variables["CONFIG"] = str(self.options.config)
        tc.cache_variables["PYTHON_EXECUTABLE"] = self._venv_python.replace("\\", "/")
        tc.cache_variables["CCACHE"] = False
        # PX4 pins its own language standard (C++14) and warning flags; the
        # profile's cppstd would only conflict with them.
        tc.blocks.remove("cppstd")
        # PX4 builds Micro-XRCE-DDS-Client as an ExternalProject that reuses this
        # toolchain file and installs into PX4's own build tree. Conan's forced
        # CMAKE_INSTALL_PREFIX would redirect that install to the package folder,
        # so drop it; package() copies artifacts by hand anyway.
        tc.blocks.remove("output_dirs")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Upstream's install() rules reproduce a ROS-workspace layout under
        # <prefix>/px4/... . Package the SITL runtime pieces directly instead:
        #   bin/px4        the daemon (plus the px4-<module> client symlinks)
        #   etc/           generated ROMFS: init.d-posix, airframes, mixers
        #   share/px4/     posix-configs startup scripts (non-SITL POSIX boards)
        copy(
            self,
            "*",
            src=os.path.join(self.build_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.build_folder, "etc"),
            dst=os.path.join(self.package_folder, "etc"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "posix-configs"),
            dst=os.path.join(self.package_folder, "share", "px4", "posix-configs"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["etc", "share"]

        bindir = os.path.join(self.package_folder, "bin")
        etcdir = os.path.join(self.package_folder, "etc")
        # Convenience for consumers launching SITL:
        #   px4 -d "$PX4_SITL_ROOTFS" -s etc/init.d-posix/rcS -w <workdir>
        for env in (self.buildenv_info, self.runenv_info):
            env.prepend_path("PATH", bindir)
            env.define_path("PX4_SITL_ROOTFS", etcdir)
