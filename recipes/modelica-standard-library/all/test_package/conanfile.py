import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import load
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    """Checks the libraries are where MODELICAPATH points, with the requested ModelicaServices."""

    test_type = "explicit"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        msl = self.dependencies["modelica-standard-library"]
        version = msl.ref.version
        libraries = os.path.join(msl.package_folder, "libraries")
        for entry in (f"Modelica {version}/package.mo", f"ModelicaServices {version}/package.mo",
                      f"Complex {version}.mo"):
            if not os.path.isfile(os.path.join(libraries, entry)):
                raise ConanException(f"{entry} missing in {libraries}")

        services = load(self, os.path.join(libraries, f"ModelicaServices {version}", "package.mo"))
        target = re.search(r'constant String target\s*=\s*"([^"]+)"', services).group(1)
        expected = {"default": "Default", "openmodelica": "OpenModelica"}[str(msl.options.modelica_services)]
        if target != expected:
            raise ConanException(f"ModelicaServices.target is {target!r}, expected {expected!r}")
        self.output.info(f"MSL {version} with ModelicaServices.target = {target!r}")

        self.run('test -d "$MODELICAPATH"', env="conanrun")
