import os
from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import copy, get, replace_in_file


class MavlinkConan(ConanFile):
    name = "mavlink"
    license = "LGPL-3.0-or-later"
    url = "https://github.com/mavlink/mavlink"
    homepage = "https://mavlink.io"
    description = "Header-only message marshalling library for drones"
    topics = ("mavlink", "drone", "robotics", "protocol")
    package_type = "header-library"

    no_copy_source = True

    def source(self):
        source_data = self.conan_data["sources"][str(self.version)]
        get(self, **source_data["mavlink"], strip_root=True)
        get(
            self,
            **source_data["pymavlink"],
            destination=os.path.join(self.source_folder, "pymavlink"),
            strip_root=True,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "pymavlink", "generator", "mavcrc.py"),
            "bytes.fromstring(buf)",
            "bytes.frombytes(buf.encode())",
        )

    def build(self):
        python = "python" if self.settings_build.os == "Windows" else "python3"
        python_dependencies = os.path.join(self.build_folder, "python-dependencies")
        self.run(
            f'{python} -m pip install '
            f'--disable-pip-version-check --no-compile '
            f'-r "{os.path.join(self.source_folder, "pymavlink", "requirements.txt")}" '
            f'--target "{python_dependencies}"'
        )

        environment = Environment()
        environment.define(
            "PYTHONPATH",
            os.pathsep.join((self.source_folder, python_dependencies)),
        )
        with environment.vars(self).apply():
            self.run(
                f'{python} -m pymavlink.tools.mavgen '
                f'--lang=C++11 --wire-protocol=2.0 '
                f'--output="{os.path.join(self.build_folder, "include", "mavlink")}" '
                f'"{os.path.join(self.source_folder, "message_definitions", "v1.0", "common.xml")}"'
            )

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.build_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.build_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "MAVLink")
        self.cpp_info.set_property("cmake_target_name", "MAVLink::mavlink")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
