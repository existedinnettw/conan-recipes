import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir


required_conan_version = ">=2.0"


class OpenUSDConan(ConanFile):
    name = "openusd"
    description = (
        "Universal Scene Description is a framework for interchanging and composing "
        "3D scene data"
    )
    license = "LicenseRef-Modified-Apache-2.0"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://openusd.org"
    topics = ("usd", "3d", "graphics", "vfx", "scene-description")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_imaging": [True, False],
        "with_opengl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_imaging": False,
        "with_opengl": False,
    }
    exports_sources = "conan-openusd-target.cmake"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.arch not in ("x86_64", "armv8"):
            raise ConanInvalidConfiguration(f"{self.ref} requires a 64-bit target")
        if self.options.with_opengl and not self.options.with_imaging:
            raise ConanInvalidConfiguration(
                f"{self.ref}: with_opengl=True requires with_imaging=True"
            )

    def requirements(self):
        # OpenUSD 26.08 is tested upstream with oneTBB 2021.9. Keep the range on
        # the oneTBB ABI-compatible release family so dependency resolution can
        # receive fixes without silently moving to a future ABI.
        self.requires(
            "onetbb/[>=2021.9.0 <2022]",
            transitive_headers=True,
            transitive_libs=True,
        )
        if self.options.with_imaging:
            self.requires(
                "opensubdiv/3.7.0",
                options={
                    "shared": False,
                    "with_tbb": True,
                    "with_opengl": bool(self.options.with_opengl),
                },
                transitive_headers=True,
                transitive_libs=True,
            )
        if self.options.with_opengl:
            self.requires(
                "opengl/system",
                transitive_headers=True,
                transitive_libs=True,
            )

    def build_requirements(self):
        # OpenUSD 26.08 raises its minimum CMake version to 3.27.
        self.tool_requires("cmake/[>=3.27 <5]")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        if self.options.with_imaging:
            # The Conan Center OpenSubdiv recipe exports lower-case target names,
            # while current OpenUSD looks for the upstream osdCPU/osdGPU spelling.
            suffix = "" if self.dependencies["opensubdiv"].options.shared else "_static"
            deps.set_property(
                "opensubdiv::osdcpu",
                "cmake_target_name",
                f"OpenSubdiv::osdCPU{suffix}",
            )
            if self.options.with_opengl:
                deps.set_property(
                    "opensubdiv::osdgpu",
                    "cmake_target_name",
                    f"OpenSubdiv::osdGPU{suffix}",
                )
        deps.generate()

        tc = CMakeToolchain(self)
        # One library gives consumers a stable target while preserving OpenUSD's
        # plugin/type-registration resources in their upstream install layout.
        tc.cache_variables["PXR_BUILD_MONOLITHIC"] = True
        tc.cache_variables["PXR_ENABLE_PYTHON_SUPPORT"] = False
        tc.cache_variables["PXR_BUILD_USD_TOOLS"] = False
        tc.cache_variables["PXR_BUILD_USDVIEW"] = False
        tc.cache_variables["PXR_BUILD_TESTS"] = False
        tc.cache_variables["PXR_BUILD_EXAMPLES"] = False
        tc.cache_variables["PXR_BUILD_TUTORIALS"] = False
        tc.cache_variables["PXR_BUILD_DOCUMENTATION"] = False

        tc.cache_variables["PXR_BUILD_IMAGING"] = bool(self.options.with_imaging)
        tc.cache_variables["PXR_BUILD_USD_IMAGING"] = bool(self.options.with_imaging)
        tc.cache_variables["PXR_ENABLE_GL_SUPPORT"] = bool(self.options.with_opengl)
        if self.settings.os in ("Macos", "iOS", "tvOS", "watchOS", "visionOS"):
            # Embedded Apple targets otherwise default to a shared framework,
            # overriding Conan's shared option and changing the package layout.
            tc.cache_variables["PXR_BUILD_APPLE_FRAMEWORK"] = False
        # Metal is not represented by this recipe yet; avoid an implicit platform-
        # dependent feature when the package ID only records the options above.
        tc.cache_variables["PXR_ENABLE_METAL_SUPPORT"] = False
        tc.cache_variables["PXR_ENABLE_VULKAN_SUPPORT"] = False
        tc.cache_variables["PXR_ENABLE_MATERIALX_SUPPORT"] = False
        tc.cache_variables["PXR_BUILD_OPENIMAGEIO_PLUGIN"] = False
        tc.cache_variables["PXR_BUILD_OPENCOLORIO_PLUGIN"] = False
        tc.cache_variables["PXR_ENABLE_OSL_SUPPORT"] = False
        tc.cache_variables["PXR_ENABLE_PTEX_SUPPORT"] = False
        tc.cache_variables["PXR_ENABLE_OPENVDB_SUPPORT"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

        # CMakeDeps supplies the relocatable consumer config. The upstream files
        # model its complete target graph and conflict with the monolithic target.
        rm(self, "pxrConfig.cmake", self.package_folder)
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        if not self.options.shared:
            copy(
                self,
                "conan-openusd-target.cmake",
                src=self.export_sources_folder,
                dst=os.path.join(self.package_folder, "lib", "cmake", "OpenUSD"),
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenUSD")
        self.cpp_info.set_property("cmake_target_name", "OpenUSD::OpenUSD")
        self.cpp_info.requires = ["onetbb::libtbb"]

        if self.options.shared:
            self.cpp_info.libs = ["usd_ms"]
            if self.settings.os == "Windows":
                # OpenUSD installs the monolithic DLL alongside its import library.
                self.cpp_info.bindirs = ["lib"]
        else:
            # A static monolithic OpenUSD relies on registration-only translation
            # units. A regular archive link discards those units, so use CMake's
            # portable WHOLE_ARCHIVE feature for the supported consumer target.
            self.cpp_info.set_property(
                "cmake_build_modules",
                [os.path.join("lib", "cmake", "OpenUSD", "conan-openusd-target.cmake")],
            )
            self.cpp_info.libs = ["usd_m"]

        if self.options.with_imaging:
            self.cpp_info.requires.append("opensubdiv::osdcpu")
            if self.options.with_opengl:
                self.cpp_info.requires.extend(["opensubdiv::osdgpu", "opengl::opengl"])

        if not self.options.shared:
            self.cpp_info.defines.append("PXR_STATIC")
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["Shlwapi", "Dbghelp", "Ws2_32"]
        elif self.settings.os in ("Macos", "iOS", "tvOS", "watchOS", "visionOS"):
            self.cpp_info.frameworks = ["Foundation"]
            if self.options.with_imaging:
                self.cpp_info.frameworks.extend(["ImageIO", "CoreGraphics"])

        # Static builds locate resources relative to the executable rather than the
        # archive, and external plugins live outside lib/usd even for shared builds.
        self.runenv_info.prepend_path(
            "PXR_PLUGINPATH_NAME", os.path.join(self.package_folder, "plugin", "usd")
        )
        self.runenv_info.prepend_path(
            "PXR_PLUGINPATH_NAME", os.path.join(self.package_folder, "lib", "usd")
        )
