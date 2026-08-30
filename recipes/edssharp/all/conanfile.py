import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file


class EDSSharpConan(ConanFile):
    name = "edssharp"
    license = "GPL-3.0-or-later"
    url = "https://github.com/CANopenNode/CANopenEditor"
    homepage = "https://github.com/CANopenNode/CANopenEditor"
    description = "CLI converter and CANopenNode object dictionary generator"
    topics = ("canopen", "eds", "xdd", "object-dictionary", "code-generation")
    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if self.settings.os != "Linux" or self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration(
                "The EDSSharp package currently supports Linux x86_64 build hosts"
            )

    def layout(self):
        self.folders.build = "build"

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

        # Source archives have no Git metadata, so replace upstream's
        # git-describe target with the deterministic Conan package version.
        project = os.path.join(self.source_folder, "libEDSsharp", "libEDSsharp.csproj")
        replace_in_file(
            self,
            project,
            '<Project Sdk="Microsoft.NET.Sdk" InitialTargets="AssignInformationalVersion">',
            '<Project Sdk="Microsoft.NET.Sdk">',
        )
        replace_in_file(
            self,
            project,
            """  <Target Name="AssignInformationalVersion" >
    <Exec Command="git describe --tags --long --dirty" ConsoleToMSBuild="true">
      <Output TaskParameter="ConsoleOutput" PropertyName="gitInfo" />
    </Exec>
    <PropertyGroup>
      <InformationalVersion>$(gitInfo)</InformationalVersion>
    </PropertyGroup>
  </Target>
  """,
            "",
        )

    def build(self):
        output = os.path.join(self.build_folder, "publish")
        project = os.path.join(self.source_folder, "EDSSharp", "EDSSharp.csproj")
        self.run(
            f'dotnet publish "{project}" '
            "--framework net8.0 "
            "--configuration Release "
            f'--output "{output}" '
            "--self-contained false "
            "-p:BuildNet8=true "
            f"-p:InformationalVersion=v{self.version}"
        )

    def package(self):
        copy(
            self,
            "License-GPLv3.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.build_folder, "publish"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "minimal_project.xdd",
            src=os.path.join(self.source_folder, "Tests"),
            dst=os.path.join(self.package_folder, "res"),
        )

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
