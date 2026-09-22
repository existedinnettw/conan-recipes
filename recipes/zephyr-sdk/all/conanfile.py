import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, get, unzip, rm
from conan.tools.scm import Version


class ZephyrSdkConan(ConanFile):
    """Zephyr SDK (GNU cross toolchains + optional Yocto host tools).

    Companion of the ``zephyr`` recipe in the "Conan outside" architecture:
    Conan pins *which* SDK a firmware build uses and exports
    ``ZEPHYR_SDK_INSTALL_DIR`` / ``ZEPHYR_TOOLCHAIN_VARIANT``; Zephyr's own
    CMake toolchain logic stays untouched (no ``conan_toolchain.cmake``).

    The SDK is a build-machine tool, so always consume it as::

        def build_requirements(self):
            self.tool_requires("zephyr-sdk/1.0.1")

    Compatibility: Zephyr >= 4.4 requires SDK 1.0.x, Zephyr 4.3 requires 0.17.x.
    """

    name = "zephyr-sdk"
    license = "Apache-2.0 AND GPL-3.0-or-later WITH GCC-exception-3.1"
    url = "https://github.com/zephyrproject-rtos/sdk-ng"
    homepage = "https://github.com/zephyrproject-rtos/sdk-ng"
    description = "Zephyr SDK: prebuilt GNU cross toolchains and host tools for building Zephyr RTOS"
    topics = ("zephyr", "sdk", "toolchain", "gcc", "cross-compile", "embedded")
    package_type = "application"

    # os/arch describe the machine the SDK runs on (the build context).
    settings = "os", "arch"
    options = {
        # Comma-separated GNU toolchain targets, e.g. "arm-zephyr-eabi,riscv64-zephyr-elf",
        # or "all". Names as in the SDK's sdk_gnu_toolchains list.
        "toolchains": ["ANY"],
        # Install the Yocto host tools bundle (qemu, openocd, dtc, ...). Linux only.
        "hosttools": [True, False],
    }
    default_options = {
        "toolchains": "arm-zephyr-eabi",
        "hosttools": False,
    }

    @property
    def _sources(self):
        return self.conan_data["sources"][str(self.version)]

    @property
    def _host(self):
        os_name = {"Linux": "linux", "Macos": "macos"}.get(str(self.settings.os))
        arch = {"x86_64": "x86_64", "armv8": "aarch64"}.get(str(self.settings.arch))
        if os_name is None or arch is None:
            return None
        return f"{os_name}-{arch}"

    @property
    def _gnu_layout(self):
        # SDK >= 1.0 places GNU toolchains under gnu/, older ones at the root.
        return Version(self.version) >= "1.0"

    @property
    def _toolchains(self):
        requested = [t.strip() for t in str(self.options.toolchains).split(",") if t.strip()]
        available = self._sources["toolchains"].get(self._host, {})
        if "all" in requested:
            return sorted(available)
        return requested

    def config_options(self):
        if self.settings.os != "Linux":
            # Upstream setup.sh: "macOS host tools are not available yet."
            self.options.rm_safe("hosttools")

    def validate(self):
        if self._host is None or self._host not in self._sources["minimal"]:
            raise ConanInvalidConfiguration(
                f"zephyr-sdk/{self.version} has no prebuilt bundle for "
                f"{self.settings.os}/{self.settings.arch} "
                f"(available: {', '.join(sorted(self._sources['minimal']))})"
            )
        available = self._sources["toolchains"].get(self._host, {})
        unknown = [t for t in self._toolchains if t not in available]
        if unknown:
            raise ConanInvalidConfiguration(
                f"Unknown zephyr-sdk toolchain(s) for {self._host}: {', '.join(unknown)}. "
                f"Available: {', '.join(sorted(available))}"
            )
        if not self._toolchains:
            raise ConanInvalidConfiguration("zephyr-sdk needs at least one toolchain (or 'all')")
        if self.options.get_safe("hosttools") and self._host not in self._sources.get("hosttools", {}):
            raise ConanInvalidConfiguration(f"No host tools bundle for {self._host}")

    def configure(self):
        # Normalise so "a,b" and "b,a" (or "all") share one package id.
        self.options.toolchains = ",".join(sorted(set(self._toolchains)))

    def _url(self, entry):
        return f"{self._sources['base_url']}/{entry['file']}"

    def build(self):
        # Everything is fetched in build() (not source()) because the toolchain
        # selection is an option and source() must be option-independent.
        sdk = os.path.join(self.build_folder, "sdk")
        minimal = self._sources["minimal"][self._host]
        get(self, self._url(minimal), sha256=minimal["sha256"], destination=sdk, strip_root=True)

        tc_dir = os.path.join(sdk, "gnu") if self._gnu_layout else sdk
        for name in self._toolchains:
            entry = self._sources["toolchains"][self._host][name]
            self.output.info(f"Installing GNU toolchain {name}")
            get(self, self._url(entry), sha256=entry["sha256"], destination=tc_dir)

        if self.options.get_safe("hosttools"):
            entry = self._sources["hosttools"][self._host]
            ht_dir = os.path.join(sdk, "hosttools") if self._gnu_layout else sdk
            self.output.info("Installing host tools")
            archive = os.path.join(self.build_folder, entry["file"])
            download(self, self._url(entry), archive, sha256=entry["sha256"])
            unzip(self, archive, destination=ht_dir)
            rm(self, entry["file"], self.build_folder)
            installer = next(
                f for f in os.listdir(ht_dir) if f.startswith("zephyr-sdk-") and f.endswith("-hosttools-standalone-0.10.sh")
            )
            # Same as setup.sh: relocatable Yocto installer, into the SDK tree.
            self.run(f"sh ./{installer} -y -d .", cwd=ht_dir)
            rm(self, installer, ht_dir)

    def package(self):
        sdk = os.path.join(self.build_folder, "sdk")
        copy(self, "*", src=sdk, dst=self.package_folder)
        # The minimal bundle carries its own license texts inside each toolchain.
        for name in self._toolchains:
            base = os.path.join(sdk, "gnu", name) if self._gnu_layout else os.path.join(sdk, name)
            copy(self, "*LICENSE*", src=base, dst=os.path.join(self.package_folder, "licenses", name), keep_path=False)
            copy(self, "*COPYING*", src=base, dst=os.path.join(self.package_folder, "licenses", name), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []

        sdk = self.package_folder
        # This is all Zephyr's FindZephyr-sdk.cmake needs; no CMake user-registry
        # registration (setup.sh -c) is performed, keeping the machine untouched.
        self.buildenv_info.define_path("ZEPHYR_SDK_INSTALL_DIR", sdk)
        # Zephyr enumerates every Zephyr-sdk CMake package it can see and takes the
        # first match of the best version, so another installed SDK of the same
        # version (e.g. one on nix's system prefix path) could shadow this one.
        # The CMAKE_PREFIX_PATH environment variable is searched before system
        # prefixes, which makes this package win. (<Pkg>_ROOT is not usable: the
        # hyphen in "Zephyr-sdk_ROOT" is not a valid shell variable name.)
        self.buildenv_info.prepend_path("CMAKE_PREFIX_PATH", sdk)
        self.buildenv_info.define("ZEPHYR_TOOLCHAIN_VARIANT", "zephyr")
        self.conf_info.define("user.zephyr-sdk:install_dir", sdk)
        self.conf_info.define("user.zephyr-sdk:toolchains", list(self._toolchains))

        # Convenience: cross gcc/gdb/objdump on PATH for the build environment.
        for name in self._toolchains:
            base = os.path.join(sdk, "gnu", name) if self._gnu_layout else os.path.join(sdk, name)
            self.buildenv_info.append_path("PATH", os.path.join(base, "bin"))
        if self.options.get_safe("hosttools"):
            host_tools = os.path.join(sdk, "hosttools") if self._gnu_layout else sdk
            self.buildenv_info.append_path(
                "PATH",
                os.path.join(host_tools, "sysroots", f"{self.settings.arch}-pokysdk-linux", "usr", "bin"),
            )
