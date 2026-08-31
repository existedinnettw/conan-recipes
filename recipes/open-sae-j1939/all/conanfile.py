import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class OpenSAEJ1939Conan(ConanFile):
    name = "open-sae-j1939"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/DanielMartensson/Open-SAE-J1939"
    description = "SAE J1939 protocol stack for embedded systems and PCs"
    topics = ("sae-j1939", "can-bus", "embedded", "automotive")
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "target_platform": [
            "NO_PLATFORM",
            "STM32",
            "ARDUINO",
            "PIC",
            "AVR",
            "QT_USB",
            "INTERNAL_CALLBACK",
            "SOCKETCAN",
        ],
        "max_proprietary_a": ["ANY"],
        "max_proprietary_b": ["ANY"],
        "max_proprietary_b_pgns": ["ANY"],
    }
    default_options = {
        "target_platform": "NO_PLATFORM",
        "max_proprietary_a": 15,
        "max_proprietary_b": 60,
        "max_proprietary_b_pgns": 2,
    }

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.options.target_platform == "SOCKETCAN" and self.settings.os != "Linux":
            raise ConanInvalidConfiguration("SocketCAN requires a Linux target")
        for option in (
            "max_proprietary_a",
            "max_proprietary_b",
            "max_proprietary_b_pgns",
        ):
            value = str(self.options.get_safe(option))
            if not value.isdigit() or int(value) <= 0:
                raise ConanInvalidConfiguration(f"{option} must be a positive integer")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["OPENSAE_J1939_TARGET_PLATFORM"] = str(
            self.options.target_platform
        )
        toolchain.variables["MAX_PROPRIETARY_A"] = str(self.options.max_proprietary_a)
        toolchain.variables["MAX_PROPRIETARY_B"] = str(self.options.max_proprietary_b)
        toolchain.variables["MAX_PROPRIETARY_B_PGNS"] = str(
            self.options.max_proprietary_b_pgns
        )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="opensaej1939")

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "Src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "*.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.lib",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["opensaej1939"]
        self.cpp_info.set_property("cmake_file_name", "OpenSAEJ1939")
        self.cpp_info.set_property(
            "cmake_target_name", "OpenSAEJ1939::opensaej1939"
        )
        self.cpp_info.defines = [
            f"OPENSAE_J1939_TARGET_PLATFORM={self.options.target_platform}",
            f"MAX_PROPRIETARY_A={self.options.max_proprietary_a}",
            f"MAX_PROPRIETARY_B={self.options.max_proprietary_b}",
            f"MAX_PROPRIETARY_B_PGNS={self.options.max_proprietary_b_pgns}",
        ]
