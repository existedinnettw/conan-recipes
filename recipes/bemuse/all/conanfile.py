import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm

required_conan_version = ">=2.0"


class BemuseConan(ConanFile):
    name = "bemuse"
    description = (
        "BEMUse: a lightweight boundary element method library for frequency-domain "
        "potential-flow hydrodynamics (radiation/diffraction) and aerodynamics"
    )
    license = "GPL-3.0-or-later"
    url = "https://github.com/ZeppSav/BEMUse"
    homepage = "https://github.com/ZeppSav/BEMUse"
    topics = ("boundary-element-method", "bem", "hydrodynamics", "potential-flow", "offshore", "openmp")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # Upstream builds single precision (SinglePrec); its headers switch the Real,
        # Vector, Matrix, ... typedefs on it.
        "precision": ["single", "double"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "precision": "single",
    }

    exports_sources = "CMakeLists.txt"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # BEMUse_Math_Types.h includes <Eigen/Eigen>; the solver headers Eigen's
        # unsupported IterativeSolvers.
        self.requires("eigen/[>=3.4.0 <4]", transitive_headers=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)
        # gettimeofday/mkdir from <sys/time.h>/<sys/stat.h>.
        if self.settings.os not in ("Linux", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux, FreeBSD and macOS")
        # The Bessel functions come from libstdc++'s <tr1/cmath>.
        if self.settings.compiler.get_safe("libcxx") not in (None, "libstdc++", "libstdc++11"):
            raise ConanInvalidConfiguration(f"{self.ref} needs libstdc++ (it uses <tr1/cmath>)")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # A copy of GCC 7's libgomp omp.h, which BEMUser_Console.cpp would pick up
        # with #include "omp.h" instead of the compiler's own.
        rm(self, "omp.h", os.path.join(self.source_folder, "src"))

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["BEMUSE_SRC_DIR"] = self.source_folder.replace("\\", "/")
        tc.cache_variables["BEMUSE_PRECISION"] = self._precision_define
        tc.generate()

    @property
    def _precision_define(self):
        return "DoublePrec" if self.options.precision == "double" else "SinglePrec"

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "LICENCE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "BEMUse")
        self.cpp_info.set_property("cmake_target_name", "BEMUse::BEMUse")
        self.cpp_info.libs = ["bemuse"]
        # The headers include each other by paths relative to upstream's src/, e.g.
        # #include "Boundary/Ellipsoid.h".
        self.cpp_info.includedirs = [os.path.join("include", "BEMUse")]
        self.cpp_info.defines = [self._precision_define]
        self.cpp_info.requires = ["eigen::eigen"]
        if self.settings.compiler in ("gcc", "clang", "apple-clang"):
            self.cpp_info.cxxflags = ["-fopenmp"]
            self.cpp_info.sharedlinkflags = ["-fopenmp"]
            self.cpp_info.exelinkflags = ["-fopenmp"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
