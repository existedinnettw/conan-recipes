import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"


class DirectXShaderCompilerConan(ConanFile):
    name = "directx-shader-compiler"
    description = ("DirectX Shader Compiler (DXC): compiles HLSL to DXIL and SPIR-V. O3DE's fork, "
                   "with its dxsc specialization-constant tool")
    license = "NCSA"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/o3de/DirectXShaderCompiler"
    topics = ("hlsl", "shader", "dxil", "spir-v", "compiler", "o3de")
    # dxc and dxsc, and the libdxcompiler shared library they use (the dxcapi.h API).
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "Macos"):
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux and macOS")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["dxc"], strip_root=True)
        for name, folder in (("spirv-headers", "SPIRV-Headers"), ("spirv-tools", "SPIRV-Tools"),
                             ("directx-headers", "DirectX-Headers")):
            get(self, **sources[name], strip_root=True, destination=os.path.join("external", folder))

    def generate(self):
        tc = CMakeToolchain(self)
        # O3DE's Linux configuration (3p-package-source's build_config.json), without the tests.
        tc.cache_variables.update({
            "LLVM_DEFAULT_TARGET_TRIPLE": "dxil-ms-dx",
            "LLVM_ENABLE_EH": True,
            "LLVM_ENABLE_RTTI": True,
            "LLVM_REQUIRES_EH": True,
            "LLVM_REQUIRES_RTTI": True,
            "LLVM_INCLUDE_DOCS": False,
            "LLVM_INCLUDE_EXAMPLES": False,
            "LLVM_INCLUDE_TESTS": False,
            "LLVM_OPTIMIZED_TABLEGEN": False,
            "LLVM_TARGETS_TO_BUILD": "None",
            "LIBCLANG_BUILD_STATIC": True,
            "CLANG_BUILD_EXAMPLES": False,
            "CLANG_CL": False,
            "CLANG_ENABLE_ARCMT": False,
            "CLANG_ENABLE_STATIC_ANALYZER": False,
            "CLANG_INCLUDE_TESTS": False,
            "HLSL_INCLUDE_TESTS": False,
            "ENABLE_SPIRV_CODEGEN": True,
            "SPIRV_BUILD_TESTS": False,
            # Newer compilers warn about code of this SPIRV-Tools commit.
            "SPIRV_WERROR": False,
            # The sources are an archive, not a git checkout.
            "HLSL_SUPPORT_QUERY_GIT_COMMIT_INFO": False,
            "LLVM_APPEND_VC_REV": False,
        })
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Only the compilers and their library: the default target is all of LLVM's tools.
        for target in ("dxc", "dxsc"):
            cmake.build(target=target)

    def package(self):
        copy(self, "LICENSE.TXT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "ThirdPartyNotices.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # dxc and dxsc are symlinks to dxc-3.7 and dxsc-3.7
        for name in ("dxc", "dxc-3.7", "dxsc", "dxsc-3.7"):
            copy(self, name, os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        for pattern in ("libdxcompiler.so*", "libdxcompiler*.dylib"):
            copy(self, pattern, os.path.join(self.build_folder, "lib"), os.path.join(self.package_folder, "lib"))
        # The public API (dxcapi.h and what it includes)
        for header in ("dxcapi.h", "WinAdapter.h", "dxcerrors.h", "dxcisense.h"):
            copy(self, header, os.path.join(self.source_folder, "include", "dxc"),
                 os.path.join(self.package_folder, "include", "dxc"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "directx-shader-compiler")
        self.cpp_info.set_property("cmake_target_name", "directx-shader-compiler::dxcompiler")
        self.cpp_info.libs = ["dxcompiler"]
        if self.settings.os == "Linux":
            # dxcapi.h loads libdxcompiler with dlopen; macOS has it in libSystem.
            self.cpp_info.system_libs = ["dl"]
