import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import build_jobs, stdcpp_library
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, replace_in_file, rm, rmdir
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class GpsdConan(ConanFile):
    name = "gpsd"
    license = "BSD-2-Clause"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://gpsd.io"
    description = (
        "Client libraries of gpsd: libgps (C) and libgpsmm (C++) for reading fixes from a running gpsd. "
        "The daemon and its tools are not packaged; install gpsd on the target from the OS."
    )
    topics = ("gpsd", "gps", "gnss", "libgps", "libgpsmm", "nmea", "ais")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libgpsmm": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_libgpsmm": True,
    }

    _platforms = {"Linux": "linux", "FreeBSD": "freebsd", "Macos": "darwin"}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        if not self.options.with_libgpsmm:
            self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) not in self._platforms:
            raise ConanInvalidConfiguration(f"{self.ref} recipe supports {', '.join(self._platforms)} only")

    def build_requirements(self):
        self.tool_requires("scons/4.6.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # SConscript reads CC, CXX, AR and *FLAGS from the environment.
        VirtualBuildEnv(self).generate()
        AutotoolsToolchain(self).generate()

    @property
    def _scons_args(self):
        def yn(value):
            return "yes" if value else "no"

        return [
            # minimal turns off every optional feature not named here, so no
            # libusb, bluez, dbus, ncurses, Qt or Python is probed or linked.
            "minimal=yes",
            # ...which also drops these client-side defaults that need no extra
            # dependency: AIS JSON parsing (AIVDM_ENABLE in libgps_json.c) and
            # gps_open(GPSD_SHARED_MEMORY, ...) (SHM_EXPORT_ENABLE).
            "aivdm=yes",
            "shm_export=yes",
            "gpsd=no",
            "gpsdclients=no",
            "python=no",
            "qt=no",
            "xgps=no",
            "manbuild=no",
            "systemd=no",
            "nostrip=yes",
            f"shared={yn(self.options.shared)}",
            f"libgpsmm={yn(self.options.with_libgpsmm)}",
            f"target_platform={self._platforms[str(self.settings.os)]}",
            f"prefix={self.package_folder}",
            "libdir=lib",
            "includedir=include",
        ]

    def _scons(self, target):
        args = " ".join(f'"{a}"' for a in self._scons_args)
        self.run(f"scons -j{build_jobs(self)} {args} {target}", cwd=self.source_folder)

    def build(self):
        # SConscript appends -O2 (or -O0 with debug=yes) to CCFLAGS, which SCons
        # puts after CFLAGS, so it would override the build_type optimization
        # coming from AutotoolsToolchain. Let the profile decide.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "SConscript"),
            """    if env['debug'] or env['coveraging']:
        env.Append(CCFLAGS=['-O0'])
    else:
        env.Append(CCFLAGS=['-O2'])""",
            "",
        )
        self._scons("build")

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        self._scons("install")
        # install also lays down the Python FFI helper, docs, icons and MIBs.
        rm(self, "libgpsdpacket*", os.path.join(self.package_folder, "lib"))
        for folder in ("bin", "sbin", "share", os.path.join("lib", "pkgconfig")):
            rmdir(self, os.path.join(self.package_folder, folder))
        if not self.options.with_libgpsmm:
            rm(self, "libgpsmm.h", os.path.join(self.package_folder, "include"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libgps")
        self.cpp_info.set_property("cmake_target_name", "libgps::libgps")
        self.cpp_info.set_property("pkg_config_name", "libgps")
        self.cpp_info.libs = ["gps"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "pthread"]
            if self.settings.os == "Linux":
                self.cpp_info.system_libs.append("rt")
        if self.options.with_libgpsmm and not self.options.shared:
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.system_libs.append(libcxx)
