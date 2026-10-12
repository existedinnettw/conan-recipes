import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"


class AzslcConan(ConanFile):
    name = "azslc"
    description = ("Amazon Shading Language (AZSL) compiler of the Open 3D Engine: translates AZSL "
                   "shaders to HLSL and emits their resource layout and reflection data")
    license = ("Apache-2.0", "MIT")
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/o3de/o3de-azslc"
    topics = ("o3de", "shader", "hlsl", "azsl", "compiler")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("antlr4-cppruntime/4.13.2")
        # Upstream's CLI11 commit is 2.1.1+2; later versions reject its positional name "- | FILE".
        self.requires("cli11/2.1.2")

    def package_id(self):
        del self.info.settings.compiler

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True, destination="src")
        copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        src = os.path.join(self.source_folder, "src")
        for license_file in ("LICENSE.txt", "LICENSE_APACHE2.TXT", "LICENSE_MIT.TXT"):
            copy(self, license_file, src, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
