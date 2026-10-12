import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        o3de = self.dependencies[self.tested_reference_str]
        gems = [g.strip() for g in str(o3de.options.gems).split(",")]
        tc = CMakeToolchain(self)
        tc.cache_variables["O3DE_TEST_ATOM"] = "Atom_RPI" in gems
        # Gem modules of a shared build are loaded at runtime, not linked.
        tc.cache_variables["O3DE_TEST_GEM_MODULES"] = not o3de.options.shared
        tc.cache_variables["O3DE_TEST_EDITOR"] = bool(o3de.options.with_editor)
        tc.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")
            o3de = self.dependencies[self.tested_reference_str]
            if o3de.options.with_asset_processor:
                # The package is an engine root the tools find above their folder. A full asset
                # build (AssetProcessorBatch --project-path=<project>) takes minutes.
                root = o3de.package_folder
                for path in ("engine.json", "Registry", os.path.join("bin", "Registry", "cmake_dependencies.assetbuilder.setreg")):
                    if not os.path.exists(os.path.join(root, path)):
                        raise ConanException(f"o3de package is missing {path}")
                self.run("AssetBuilder --help", env="conanrun")
            if o3de.options.with_launcher:
                # Running it needs a display: O3DE.GameLauncher --project-path=<project with processed assets>
                for path in (os.path.join("bin", "O3DE.GameLauncher"),
                             os.path.join("bin", "Registry", "cmake_dependencies.client.setreg")):
                    if not os.path.exists(os.path.join(o3de.package_folder, path)):
                        raise ConanException(f"o3de package is missing {path}")
