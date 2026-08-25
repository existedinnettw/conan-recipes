import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.scm import Version


class XenomaiConan(ConanFile):
    name = "xenomai"
    license = "GPL-2.0-only AND LGPL-2.1-only"
    homepage = "https://xenomai.org"
    url = "https://source.denx.de/Xenomai/xenomai"
    description = "Xenomai 3 user-space libraries and headers"
    topics = ("realtime", "xenomai", "cobalt", "rtdm", "rtcan")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "pshared": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "pshared": True,
    }

    exports_sources = (
        "test_package/CMakeLists.txt",
        "test_package/conanfile.py",
        "test_package/test_package.c",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("Xenomai Cobalt supports Linux targets only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        self.run(os.path.join(self.source_folder, "scripts", "bootstrap"))

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--with-core=cobalt",
                f"--{'enable' if self.options.pshared else 'disable'}-pshared",
                "--disable-demo",
                "--disable-testsuite",
            ]
        )
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) >= "14":
            # Xenomai 3.3.3 enables -Werror. GCC 14 reports a false positive in
            # lib/analogy/math.c after inlining vec_householder().
            tc.extra_cflags.append("-Wno-error=maybe-uninitialized")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        for license_file in ("COPYING", "LICENSE"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )
        copy(
            self,
            "COPYING",
            src=os.path.join(self.source_folder, "lib"),
            dst=os.path.join(self.package_folder, "licenses", "lib"),
            keep_path=True,
        )

        autotools = Autotools(self)
        autotools.install()

        # `make install` also stages administration utilities and kernel udev
        # rules. This package intentionally contains only the user-space SDK
        # and the two build helpers used to consume it.
        shutil.rmtree(os.path.join(self.package_folder, "etc"), ignore_errors=True)
        shutil.rmtree(os.path.join(self.package_folder, "share"), ignore_errors=True)
        shutil.rmtree(
            os.path.join(self.package_folder, "include", "cobalt", "kernel"),
            ignore_errors=True,
        )
        bin_folder = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_folder):
            for filename in os.listdir(bin_folder):
                if filename not in ("xeno", "xeno-config"):
                    path = os.path.join(bin_folder, filename)
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)

        for root, _, files in os.walk(self.package_folder):
            for filename in files:
                if filename.endswith(".la"):
                    os.unlink(os.path.join(root, filename))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Xenomai")
        self.cpp_info.set_property("cmake_target_name", "Xenomai::Xenomai")

        cobalt = self.cpp_info.components["cobalt"]
        cobalt.libs = ["cobalt"]
        cobalt.requires = ["modechk"]
        cobalt.includedirs = ["include/cobalt", "include"]
        cobalt.defines = ["_GNU_SOURCE", "_REENTRANT", "__COBALT__", "__COBALT_WRAP__"]
        cobalt.system_libs = ["pthread", "rt", "dl"]
        cobalt.exelinkflags = [
            "-Wl,--no-as-needed",
            f"-Wl,@{os.path.join(self.package_folder, 'lib', 'cobalt.wrappers')}",
            f"-Wl,@{os.path.join(self.package_folder, 'lib', 'modechk.wrappers')}",
            os.path.join(self.package_folder, "lib", "xenomai", "bootstrap.o"),
            "-Wl,--wrap=main",
            f"-Wl,--dynamic-list={os.path.join(self.package_folder, 'lib', 'dynlist.ld')}",
        ]
        cobalt.set_property("cmake_target_name", "Xenomai::cobalt")
        cobalt.set_property("pkg_config_name", "xenomai-cobalt")

        rtdm = self.cpp_info.components["rtdm"]
        rtdm.requires = ["cobalt"]
        rtdm.set_property("cmake_target_name", "Xenomai::rtdm")

        copperplate = self.cpp_info.components["copperplate"]
        copperplate.libs = ["copperplate"]
        copperplate.requires = ["cobalt"]
        copperplate.set_property("cmake_target_name", "Xenomai::copperplate")

        for component in ("alchemy", "psos", "vxworks", "smokey"):
            info = self.cpp_info.components[component]
            info.libs = [component]
            info.requires = ["copperplate"]
            info.set_property("cmake_target_name", f"Xenomai::{component}")

        analogy = self.cpp_info.components["analogy"]
        analogy.libs = ["analogy"]
        analogy.requires = ["cobalt"]
        analogy.set_property("cmake_target_name", "Xenomai::analogy")

        modechk = self.cpp_info.components["modechk"]
        modechk.libs = ["modechk"]
        modechk.set_property("cmake_target_name", "Xenomai::modechk")

        trank = self.cpp_info.components["trank"]
        trank.libs = ["trank"]
        trank.requires = ["alchemy"]
        trank.set_property("cmake_target_name", "Xenomai::trank")

        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.define("DESTDIR", self.package_folder)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define("DESTDIR", self.package_folder)
