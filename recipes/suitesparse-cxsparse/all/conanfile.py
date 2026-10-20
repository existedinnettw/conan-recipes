import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, load, rm, rmdir, save


class SuiteSparseCXSparseConan(ConanFile):
    name = "suitesparse-cxsparse"
    description = "CXSparse: a Concise Sparse matrix package - Extended (from SuiteSparse)"
    license = ("LGPL-2.1-or-later", "BSD-3-Clause")
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/DrTimothyAldenDavis/SuiteSparse"
    topics = ("sparse", "matrix", "linear-algebra", "suitesparse")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_complex": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_complex": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            # MSVC has no C99 complex type.
            self.options.with_complex = False

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Only SuiteSparse_config (which cs.h includes) and CXSparse from the superbuild.
        tc.cache_variables["SUITESPARSE_ENABLE_PROJECTS"] = "suitesparse_config;cxsparse"
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.cache_variables["CXSPARSE_USE_COMPLEX"] = bool(self.options.with_complex)
        tc.cache_variables["SUITESPARSE_REQUIRE_BLAS"] = False
        # Without a BLAS, SuiteSparse_config still expands an unquoted ${BLA_VENDOR}.
        tc.cache_variables["BLA_VENDOR"] = "Generic"
        tc.cache_variables["SUITESPARSE_CONFIG_USE_OPENMP"] = False
        tc.cache_variables["SUITESPARSE_USE_OPENMP"] = False
        tc.cache_variables["SUITESPARSE_USE_FORTRAN"] = False
        tc.cache_variables["SUITESPARSE_USE_CUDA"] = False
        tc.cache_variables["SUITESPARSE_DEMOS"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        licenses = os.path.join(self.package_folder, "licenses")
        save(self, os.path.join(licenses, "CXSparse-License.txt"),
             load(self, os.path.join(self.source_folder, "CXSparse", "Doc", "License.txt")))
        # Top-level summary; covers SuiteSparse_config (BSD-3-Clause).
        save(self, os.path.join(licenses, "SuiteSparse-LICENSE.txt"),
             load(self, os.path.join(self.source_folder, "LICENSE.txt")))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CXSparse")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::CXSparse")
        self.cpp_info.set_property("pkg_config_name", "CXSparse")
        includedirs = [os.path.join("include", "suitesparse")]
        static_suffix = "_static" if self.settings.os == "Windows" and not self.options.shared else ""

        config = self.cpp_info.components["config"]
        config.set_property("cmake_target_name", "SuiteSparse::SuiteSparseConfig")
        config.libs = [f"suitesparseconfig{static_suffix}"]
        config.includedirs = includedirs
        if self.settings.os in ("Linux", "FreeBSD"):
            config.system_libs = ["m"]

        cxsparse = self.cpp_info.components["cxsparse"]
        cxsparse.set_property("cmake_target_name", "SuiteSparse::CXSparse")
        cxsparse.libs = [f"cxsparse{static_suffix}"]
        cxsparse.includedirs = includedirs
        cxsparse.requires = ["config"]
        if not self.options.with_complex:
            cxsparse.defines = ["NCOMPLEX"]
        if self.settings.os in ("Linux", "FreeBSD"):
            cxsparse.system_libs = ["m"]
