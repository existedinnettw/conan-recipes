import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir, save


class G2oConan(ConanFile):
    name = "g2o"
    description = "g2o: a General Framework for Graph Optimization"
    license = ("BSD-2-Clause", "LGPL-3.0-or-later")
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/RainerKuemmerle/g2o"
    topics = ("graph-optimization", "slam", "bundle-adjustment", "least-squares")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_csparse": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_csparse": True,
        "with_openmp": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/3.4.0", transitive_headers=True)
        if self.options.with_csparse:
            self.requires("suitesparse-cxsparse/4.4.2", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 14)
        if self.options.with_openmp and self.settings.compiler not in ("gcc", "clang"):
            raise ConanInvalidConfiguration(f"{self.ref} with_openmp is only supported with gcc and clang")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Upstream looks for cs.h/libcxsparse by hand in system paths; use the Conan package.
        save(
            self,
            os.path.join(self.source_folder, "cmake_modules", "FindCSparse.cmake"),
            "find_package(CXSparse CONFIG QUIET)\n"
            "set(CSPARSE_FOUND ${CXSparse_FOUND})\n"
            "set(CSPARSE_INCLUDE_DIR \"\")\n"
            "set(CSPARSE_LIBRARY SuiteSparse::CXSparse)\n",
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["G2O_USE_CSPARSE"] = bool(self.options.with_csparse)
        tc.cache_variables["G2O_USE_OPENMP"] = bool(self.options.with_openmp)
        tc.cache_variables["G2O_USE_CHOLMOD"] = False
        tc.cache_variables["G2O_USE_OPENGL"] = False
        tc.cache_variables["G2O_USE_VENDORED_CERES"] = True
        tc.cache_variables["G2O_BUILD_APPS"] = False
        tc.cache_variables["G2O_BUILD_EXAMPLES"] = False
        tc.cache_variables["G2O_BUILD_PLAYGROUND"] = False
        tc.cache_variables["BUILD_UNITTESTS"] = False
        # Host-CPU detection would make the binary depend on the build machine.
        tc.cache_variables["DO_SSE_AUTODETECT"] = False
        # With detection off, every SSE level defaults to enabled; keep only the x86_64 baseline.
        tc.cache_variables["DISABLE_SSE2"] = self.settings.arch != "x86_64"
        for sse in ("SSE3", "SSE4_1", "SSE4_2", "SSE4_A"):
            tc.cache_variables[f"DISABLE_{sse}"] = True
        tc.cache_variables["BUILD_WITH_MARCH_NATIVE"] = False
        for config in ("DEBUG", "RELEASE", "RELWITHDEBINFO", "MINSIZEREL"):
            tc.cache_variables[f"CMAKE_{config}_POSTFIX"] = ""
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_SuiteSparse"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_QGLViewer"] = True
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        for license_file in ("license-bsd.txt", "license-lgpl.txt"):
            copy(self, license_file, os.path.join(self.source_folder, "doc"),
                 os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    @property
    def _components(self):
        components = {
            "stuff": ["eigen::eigen"],
            "core": ["stuff", "ceres_ad", "eigen::eigen"],
            "solver_dense": ["core"],
            "solver_eigen": ["core"],
            "solver_pcg": ["core"],
            "solver_structure_only": ["core"],
            "solver_slam2d_linear": ["solver_eigen", "types_slam2d"],
            "types_slam2d": ["core"],
            "types_slam2d_addons": ["types_slam2d", "core"],
            "types_data": ["types_slam2d", "core"],
            "types_sclam2d": ["types_slam2d", "core"],
            "types_slam3d": ["core"],
            "types_slam3d_addons": ["types_slam3d", "core"],
            "types_sba": ["types_slam3d", "core"],
            "types_icp": ["types_sba", "types_slam3d"],
            "types_sim3": ["types_sba"],
        }
        if self.options.with_csparse:
            components["csparse_extension"] = ["stuff", "suitesparse-cxsparse::cxsparse", "eigen::eigen"]
            components["solver_csparse"] = ["csparse_extension", "core"]
        return components

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "g2o")

        ceres_ad = self.cpp_info.components["ceres_ad"]
        ceres_ad.set_property("cmake_target_name", "g2o::g2o_ceres_ad")
        ceres_ad.libdirs = []
        ceres_ad.bindirs = []

        for name, requires in self._components.items():
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", f"g2o::{name}")
            component.libs = [f"g2o_{name}"]
            component.requires = requires
            if self.settings.os in ("Linux", "FreeBSD"):
                component.system_libs = ["m"]
        self.cpp_info.components["core"].defines = ["G2O_USE_VENDORED_CERES"]
        if self.options.with_openmp:
            openmp_flag = ["-fopenmp"]
            for component in self.cpp_info.components.values():
                component.cxxflags = openmp_flag
                component.sharedlinkflags = openmp_flag
                component.exelinkflags = openmp_flag
