import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save

required_conan_version = ">=2.0"


class SapienConan(ConanFile):
    name = "sapien"
    description = ("SAPIEN: a SimulAted Part-based Interactive ENvironment; C++ library with "
                   "PhysX 5 simulation and the sapien-vulkan-2 renderer")
    # Apache-2.0 for SAPIEN and sapien-vulkan-2; MIT for the imgui, ImGuizmo and
    # ImGuiFileDialog sources compiled into libsvulkan2.
    license = ("Apache-2.0", "MIT")
    url = "https://github.com/haosulab/SAPIEN"
    homepage = "https://sapien.ucsd.edu"
    topics = ("simulation", "robotics", "physics", "physx", "rendering", "vulkan", "embodied-ai")
    # Upstream hard-codes SHARED for libsapien and libsvulkan2.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "conan_deps.cmake", os.path.join(self.recipe_folder, "cmake"),
             os.path.join(self.export_sources_folder, "src", "conan"))

    def configure(self):
        # Only libktx is used; ktx's tools refuse any C++ standard above 17.
        self.options["ktx"].tools = False

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Public headers expose Eigen, PhysX, glm and Vulkan-Hpp types.
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("physx/5.3.1", transitive_headers=True)
        self.requires("glm/1.0.3", transitive_headers=True)
        self.requires("vulkan-headers/1.3.296.0", transitive_headers=True)
        self.requires("spdlog/1.15.3")
        self.requires("assimp/5.4.3")
        self.requires("glfw/3.4")
        self.requires("ktx/4.4.2")
        self.requires("glslang/1.4.313.0")
        self.requires("spirv-cross/1.4.357.0")
        self.requires("openexr/3.2.11")
        self.requires("openvr/1.16.8")

    def validate(self):
        check_min_cppstd(self, 20)
        # Upstream builds Linux wheels only from source; Windows/macOS paths are untested here.
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} recipe only supports Linux")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.24]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["sapien"], strip_root=True)
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["sapien-vulkan-2"], strip_root=True,
            destination=os.path.join(self.source_folder, "3rd_party", "sapien-vulkan-2"))
        for name in ("imgui", "imguizmo", "imguifiledialog"):
            get(self, **sources[name], strip_root=True,
                destination=os.path.join(self.source_folder, "conan", name))
        apply_conandata_patches(self)

        # FetchContent modules: the targets come from conan/conan_deps.cmake instead.
        modules = {
            "cmake": ("physx5", "zlib", "eigen", "vulkan"),
            os.path.join("3rd_party", "sapien-vulkan-2", "cmake"): (
                "glm", "assimp", "spdlog", "glfw", "ktx", "vulkan", "glslang", "spirv-cross",
                "imgui", "openexr", "openvr", "oidn"),
        }
        for folder, names in modules.items():
            for name in names:
                save(self, os.path.join(self.source_folder, folder, f"{name}.cmake"),
                     "# Provided by conan_deps.cmake (CMAKE_PROJECT_INCLUDE).\n")

        # Upstream installs the FetchContent'ed dependencies with SAPIEN; package() copies
        # the two libraries and their headers instead.
        sapien_cmake = os.path.join(self.source_folder, "CMakeLists.txt")
        content = load(self, sapien_cmake)
        content = content.replace("project(sapien LANGUAGES C CXX CUDA)", "project(sapien LANGUAGES C CXX)")
        content = re.sub(r"if \(\$\{SAPIEN_CUDA\}\)\n    add_dependencies\(sapien OpenImageDenoise_device_cuda\).*?"
                         r"(?=if \(SAPIEN_BUILD_PYTHON\))", "", content, flags=re.DOTALL)
        save(self, sapien_cmake, content)

        svulkan2_cmake = os.path.join(self.source_folder, "3rd_party", "sapien-vulkan-2", "CMakeLists.txt")
        content = load(self, svulkan2_cmake)
        content = re.sub(r"if \(\$\{SVULKAN2_CUDA_INTEROP\}\)\n    install\(TARGETS.*?(?=add_executable\(svulkan2_main)",
                         "", content, flags=re.DOTALL)
        save(self, svulkan2_cmake, content)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_INCLUDE"] = os.path.join(self.source_folder, "conan", "conan_deps.cmake").replace("\\", "/")
        tc.cache_variables["SAPIEN_IMGUI_SOURCE_DIR"] = os.path.join(self.source_folder, "conan").replace("\\", "/")
        # CUDA (GPU PhysX, CUDA-Vulkan interop, OIDN/OptiX denoisers, simsense) is not supported.
        tc.cache_variables["SAPIEN_CUDA"] = False
        # NVTX markers; NVTX comes with the CUDA toolkit.
        tc.cache_variables["SAPIEN_PROFILE"] = False
        tc.cache_variables["SAPIEN_BUILD_PYTHON"] = False
        tc.cache_variables["SAPIEN_BUILD_TEST"] = False
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="sapien")

    def package(self):
        # sapien-vulkan-2 has no license file; its sources carry SAPIEN's Apache-2.0 header.
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        svulkan2_src = os.path.join(self.source_folder, "3rd_party", "sapien-vulkan-2")
        for name in ("imgui", "imguizmo", "imguifiledialog"):
            copy(self, "LICENSE*", os.path.join(self.source_folder, "conan", name),
                 os.path.join(self.package_folder, "licenses", name))

        include = os.path.join(self.package_folder, "include")
        copy(self, "*", os.path.join(self.source_folder, "include"), include)
        copy(self, "*", os.path.join(svulkan2_src, "include"), include)
        copy(self, "*.so*", self.build_folder, os.path.join(self.package_folder, "lib"), keep_path=False)

        # GLSL shaders loaded at run time (SapienRendererDefault::set*ShaderDirectory).
        copy(self, "*", os.path.join(self.source_folder, "vulkan_shader"),
             os.path.join(self.package_folder, "res", "sapien", "vulkan_shader"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sapien")
        self.cpp_info.set_property("cmake_target_name", "sapien::sapien")
        self.cpp_info.libs = ["sapien", "svulkan2"]
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.defines = ["VK_NO_PROTOTYPES", "VULKAN_HPP_STORAGE_SHARED", "NVTX_DISABLE=1"]
        self.cpp_info.system_libs = ["dl", "pthread"]
        # Consumers point SapienRendererDefault at this folder (it has default/, rt/, ...).
        self.runenv_info.define_path("SAPIEN_SHADER_DIR",
                                     os.path.join(self.package_folder, "res", "sapien", "vulkan_shader"))
