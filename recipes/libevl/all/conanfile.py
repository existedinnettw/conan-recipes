import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, rm, rmdir, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibevlConan(ConanFile):
    name = "libevl"
    license = "MIT"
    homepage = "https://v4.xenomai.org"
    url = "https://gitlab.com/Xenomai/xenomai4/libevl"
    description = "EVL user-space library and utilities (Xenomai 4)"
    topics = ("realtime", "xenomai", "evl", "dovetail")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "uapi": ["ANY"],
        "utilities": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        # Empty means "use the EVL kernel uapi headers pinned in conandata.yml".
        # Set it to the source tree of the EVL kernel that will run the
        # application (or to the directory its `make headers_install` produced)
        # whenever that kernel exposes a different EVL ABI.
        "uapi": "",
        "utilities": True,
    }

    exports_sources = (
        "test_package/CMakeLists.txt",
        "test_package/conanfile.py",
        "test_package/test_package.c",
    )

    # EVL names its architectures the way the kernel does.
    _kernel_arch_map = {
        "x86_64": "x86",
        "armv7": "arm",
        "armv7hf": "arm",
        "armv8_32": "arm",
        "armv8": "arm64",
        "armv8.3": "arm64",
        "armv8.5": "arm64",
        "armv8.6": "arm64",
        "armv8.7": "arm64",
        "armv8.8": "arm64",
        "armv8.9": "arm64",
        "riscv64": "riscv",
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # lib/net.c and the evl-net utility are built against libbpf.
        self.requires("libbpf/1.3.0")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2 <2]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("EVL is a Linux (Dovetail) real-time core")

        if not self.options.shared and self.options.utilities:
            # Upstream declares the library dependency of `evl` and friends
            # from both_libraries(), which links them against libevl.so
            # whatever meson's default_library says.
            raise ConanInvalidConfiguration(
                "the EVL utilities link against libevl.so; build them with "
                "-o libevl/*:shared=True, or drop them with "
                "-o libevl/*:utilities=False"
            )

        if self._kernel_arch is None:
            raise ConanInvalidConfiguration(
                f"EVL has no port for settings.arch={self.settings.arch}"
            )

        if not self._uapi_option and self._kernel_arch not in self._uapi_data["arch"]:
            # The pinned kernel publishes no arch/<arch>/include/uapi/asm/evl,
            # which a tree carrying that port would.
            raise ConanInvalidConfiguration(
                f"conandata.yml pins no EVL uapi headers for {self._kernel_arch}; "
                "build with -o libevl/*:uapi=<path to an EVL kernel tree> instead"
            )

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)]["libevl"],
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()

        uapi = self._uapi_option
        if uapi:
            self.output.info(f"Building against the EVL uapi headers in {uapi}")
        else:
            uapi = self._stage_uapi_headers()

        tc = MesonToolchain(self)
        tc.project_options["uapi"] = uapi
        tc.project_options["install-uapi"] = True
        # Keep the layout Conan expects instead of the distribution one Meson
        # would derive from the host (lib/<triplet> on Debian derivatives).
        tc.project_options["libdir"] = "lib"
        tc.project_options["libexecdir"] = "libexec"
        # Upstream compiles at warning level 3 with -Werror, which breaks on
        # compilers newer than the release was tested against.
        tc.project_options["werror"] = False
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        meson = Meson(self)
        meson.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

        # Upstream builds both library flavours unconditionally, so drop the
        # one that was not asked for.
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            rm(self, "*.a", libdir)
        else:
            rm(self, "*.so*", libdir)

        if not self.options.utilities:
            rmdir(self, os.path.join(self.package_folder, "bin"))
            rmdir(self, os.path.join(self.package_folder, "libexec"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "evl")
        self.cpp_info.set_property("cmake_file_name", "evl")
        self.cpp_info.set_property("cmake_target_name", "evl::evl")

        self.cpp_info.libs = ["evl"]
        self.cpp_info.system_libs = ["pthread", "rt"]

        if not self.options.utilities:
            self.cpp_info.bindirs = []

    @property
    def _uapi_data(self):
        return self.conan_data["sources"][str(self.version)]["uapi"]

    @property
    def _uapi_option(self):
        return str(self.options.uapi) or None

    @property
    def _kernel_arch(self):
        return self._kernel_arch_map.get(str(self.settings.arch))

    def _stage_uapi_headers(self):
        """Lay out the pinned EVL uapi headers as a minimal kernel source tree.

        meson/setup-uapi.sh accepts either a kernel tree (recognized by its
        top-level Kbuild) or a `make headers_install` directory. The tree form
        is the one the two archives below already match.
        """
        folder = os.path.join(self.build_folder, "uapi-tree")
        uapi = self._uapi_data
        self.output.info(
            f"Building against the EVL ABI {uapi['abi_level']} uapi headers "
            f"of linux-evl {uapi['ref']}"
        )

        get(
            self,
            **uapi["include"],
            destination=folder,
            filename="evl-uapi-include.tar.gz",
            strip_root=True,
        )
        get(
            self,
            **uapi["arch"][self._kernel_arch],
            destination=folder,
            filename="evl-uapi-arch.tar.gz",
            strip_root=True,
        )
        save(
            self,
            os.path.join(folder, "Kbuild"),
            f"# EVL uapi headers extracted from linux-evl {uapi['ref']}\n",
        )

        return folder
