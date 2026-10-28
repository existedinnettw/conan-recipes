import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, load, save

required_conan_version = ">=2.9"


class UsdBrepConan(ConanFile):
    name = "usd-brep"
    description = (
        "USD BRep: the SMLib solid modeling kernel and libraries that read and write "
        "boundary-representation solids in OpenUSD as BrepArray prims"
    )
    license = "Apache-2.0"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/NVIDIA-Omniverse/usd-brep"
    topics = ("brep", "cad", "solid-modeling", "nurbs", "usd", "openusd", "omniverse")
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_usd": [True, False],
        "with_hydra": [True, False],
        "with_tools": [True, False],
    }
    default_options = {
        "with_usd": True,
        "with_hydra": False,
        "with_tools": True,
        # Hydra is the only part that needs imaging (OpenGL, X11, OpenSubdiv).
        "openusd/*:with_imaging": False,
    }

    def export_sources(self):
        # Lands at the root of the upstream sources, which have no CMakeLists.txt.
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def configure(self):
        if not self.options.with_usd:
            self.options.rm_safe("with_hydra")
            self.options.rm_safe("with_tools")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # The same oneTBB as openusd's; SMLib uses it for parallel_for and scalable_allocator.
        self.requires("onetbb/2023.1.0", transitive_headers=True, transitive_libs=True)
        if self.options.with_usd:
            self.requires("openusd/26.08", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} recipe is only validated on Linux")
        check_min_cppstd(self, 17)
        if self.options.get_safe("with_hydra") and not self.dependencies["openusd"].options.with_imaging:
            raise ConanInvalidConfiguration(f"{self.ref}:with_hydra requires -o openusd/*:with_imaging=True")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["USD_BREP_WITH_USD"] = bool(self.options.with_usd)
        tc.cache_variables["USD_BREP_WITH_HYDRA"] = bool(self.options.get_safe("with_hydra"))
        tc.cache_variables["USD_BREP_WITH_TOOLS"] = bool(self.options.get_safe("with_tools"))
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "THIRD_PARTY_NOTICES.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.options.with_usd:
            # The codeless omniSolid schema, registered at run time from OMNISOLID_PLUGIN_PATH.
            copy(self, "*", os.path.join(self.source_folder, "source", "schema", "omniSolid", "resources"),
                 os.path.join(self.package_folder, "res", "omniSolid", "resources"))
        if self.options.get_safe("with_hydra"):
            manifest = json.loads(load(self, os.path.join(self.source_folder, "source", "HYDRA_USD_BREP",
                                                          "resources", "plugInfo.json")))
            # Conan's openusd has no Python, so leave out the usdview plugin.
            manifest["Plugins"] = [p for p in manifest["Plugins"] if p["Type"] != "python"]
            manifest["Plugins"][0]["LibraryPath"] = "../../lib/libHYDRA_USD_BREP.so"
            save(self, os.path.join(self.package_folder, "res", "hdUsdBrep", "plugInfo.json"),
                 json.dumps(manifest, indent=4) + "\n")

    def _add_component(self, name, requires, lib=True):
        component = self.cpp_info.components[name]
        component.set_property("cmake_target_name", f"usd-brep::{name}")
        component.includedirs = [os.path.join("include", "usd-brep", name)]
        if lib:
            component.libs = [name]
        component.requires = requires
        return component

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "usd-brep")
        self.cpp_info.set_property("cmake_target_name", "usd-brep::usd-brep")

        smlib = self._add_component("SMLib", ["onetbb::libtbb", "onetbb::tbbmalloc"])
        # SmConfig.h changes class layouts with these, as upstream's build sets them.
        smlib.defines = ["SM_GRAPHICS_CALLBACKS=1"]
        if self.settings.build_type == "Debug":
            smlib.defines.extend(["SM_DEBUG_CODE=1", "SM_GFX_CODE=1"])
        smlib.system_libs = ["m", "pthread"]
        self._add_component("SM_API", ["SMLib"])

        if not self.options.with_usd:
            return
        usd = [f"openusd::{c}" for c in ("ar", "arch", "gf", "js", "kind", "pcp", "plug", "sdf", "sdr", "tf",
                                          "trace", "usd", "usdGeom", "usdLux", "usdShade", "usdUtils",
                                          "usdVol", "vt", "work")]
        data = self._add_component("BREP_USD_DATA", usd)
        data.resdirs = ["res"]
        self._add_component("USD_BREP_UTILS", ["BREP_USD_DATA"])
        self._add_component("BREP_STAGING", ["BREP_USD_DATA"])
        self._add_component("OCCT_BREP_IMPORT", ["BREP_STAGING"])
        self._add_component("OCCT_BREP_EXPORT", ["USD_BREP_UTILS"])
        # OCCT_BREP_EXPORT's headers use the importer's record structs.
        self.cpp_info.components["OCCT_BREP_EXPORT"].includedirs.append(
            os.path.join("include", "usd-brep", "OCCT_BREP_IMPORT"))
        self._add_component("BREP_SM_USD", ["SMLib", "BREP_USD_DATA"])
        self._add_component("SM_API_USD", ["SM_API", "BREP_SM_USD"])

        schema = os.path.join(self.package_folder, "res", "omniSolid", "resources")
        self.runenv_info.define_path("OMNISOLID_PLUGIN_PATH", schema)
        self.buildenv_info.define_path("OMNISOLID_PLUGIN_PATH", schema)

        if self.options.with_hydra:
            # Loaded by USD's plugin registry from PXR_PLUGINPATH_NAME, not linked.
            hydra = self._add_component("HYDRA_USD_BREP", ["SM_API_USD"] + [
                f"openusd::{c}" for c in ("hd", "hdGp", "usdImaging", "hf", "pxOsd")])
            hydra.libs = []
            plugin = os.path.join(self.package_folder, "res", "hdUsdBrep")
            self.runenv_info.prepend_path("PXR_PLUGINPATH_NAME", plugin)

        if self.options.with_tools:
            # A library package's bin/ is not put on PATH by default.
            self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
