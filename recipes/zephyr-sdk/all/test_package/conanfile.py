import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import save


class TestPackageConan(ConanFile):
    """Checks the SDK is discoverable the way Zephyr discovers it.

    1. ``find_package(Zephyr-sdk)`` resolves via ZEPHYR_SDK_INSTALL_DIR only.
    2. Every requested cross compiler runs.
    """

    test_type = "explicit"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def build(self):
        sdk = self.dependencies.build["zephyr-sdk"]
        version = sdk.ref.version
        major_minor = ".".join(str(version).split(".")[:2])
        script = os.path.join(self.build_folder, "find_sdk.cmake")
        save(
            self,
            script,
            "\n".join(
                [
                    "cmake_minimum_required(VERSION 3.20)",
                    f"find_package(Zephyr-sdk {major_minor} REQUIRED CONFIG HINTS $ENV{{ZEPHYR_SDK_INSTALL_DIR}})",
                    'message(STATUS "Zephyr-sdk ${Zephyr-sdk_VERSION} at ${ZEPHYR_SDK_INSTALL_DIR}")',
                    "",
                ]
            ),
        )
        self.run(f"cmake -P {script}")

        for name in sdk.conf_info.get("user.zephyr-sdk:toolchains", check_type=list):
            self.run(f"{name}-gcc --version")

    def test(self):
        sdk_dir = self.dependencies.build["zephyr-sdk"].conf_info.get("user.zephyr-sdk:install_dir")
        if not os.path.isfile(os.path.join(sdk_dir, "sdk_version")):
            raise ConanException(f"sdk_version missing in {sdk_dir}")
