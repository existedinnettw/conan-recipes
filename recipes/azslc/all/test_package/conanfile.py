import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.errors import ConanException
from conan.tools.files import load, save
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if can_run(self):
            shader = os.path.join(self.build_folder, "test.azsl")
            save(self, shader, """
ShaderResourceGroupSemantic SRG_PerDraw { FrequencyId = 0; };
ShaderResourceGroup DrawSrg : SRG_PerDraw
{
    float4 m_color;
};

float4 MainPS() : SV_Target0
{
    return DrawSrg::m_color;
}
""")
            self.run("azslc --version")
            hlsl = os.path.join(self.build_folder, "test.hlsl")
            self.run(f"azslc {shader} --namespace=vk -o {hlsl}")
            if "MainPS" not in load(self, hlsl):
                raise ConanException("azslc did not emit the shader's entry point")
