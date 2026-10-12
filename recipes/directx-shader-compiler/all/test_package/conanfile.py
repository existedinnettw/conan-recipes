import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import save


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # The dxcapi.h library API
            self.run(os.path.join(self.cpp.build.bindir, "test_package"), env="conanrun")
            # The compiler, to DXIL and to SPIR-V
            shader = os.path.join(self.build_folder, "test.hlsl")
            save(self, shader, "float4 main(float4 color : COLOR) : SV_Target { return color * 0.5f; }\n")
            self.run(f"dxc -T ps_6_0 -E main {shader} -Fo {shader}.dxil", env="conanrun")
            self.run(f"dxc -spirv -T ps_6_0 -E main {shader} -Fo {shader}.spv", env="conanrun")
            if not os.path.getsize(f"{shader}.spv"):
                raise ConanException("dxc emitted no SPIR-V")
            # O3DE's tool for patching specialization constants
            self.run("dxsc --help", env="conanrun")
