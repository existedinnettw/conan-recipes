import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch"
    generators = "VirtualBuildEnv"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def test(self):
        package_folder = self.dependencies.build["edssharp"].package_folder
        input_file = os.path.join(package_folder, "res", "minimal_project.xdd")
        output_base = os.path.join(self.build_folder, "OD.c")
        self.run(
            "EDSSharp "
            f"--infile {shlex.quote(input_file)} "
            f"--outfile {shlex.quote(output_base)} "
            "--type CanOpenNodeV4",
            env="conanbuild",
        )

        for filename in ("OD.c", "OD.h"):
            output = os.path.join(self.build_folder, filename)
            if not os.path.isfile(output) or os.path.getsize(output) == 0:
                raise ConanException(f"EDSSharp did not generate {output}")

