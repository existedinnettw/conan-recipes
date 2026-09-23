import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir


class NlfConan(ConanFile):
    name = "nlf"
    description = (
        "Modern Computational Nonlinear Filtering: EKF, UKF, SRUKF, particle and "
        "Rao-Blackwellized particle filters and smoothers on Eigen, with the "
        "OptMathKernels NEON/SVE2 backends"
    )
    license = "MIT"
    url = "https://github.com/n4hy/Modern-Computational-Nonlinear-Filtering"
    homepage = "https://github.com/n4hy/Modern-Computational-Nonlinear-Filtering"
    topics = ("kalman-filter", "ukf", "ekf", "particle-filter", "smoother", "estimation")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # The filters are Eigen templates and expose Eigen types in their API.
        self.requires("eigen/3.4.0", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 20)

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _optmath_folder(self):
        return os.path.join(self.source_folder, "OptimizedKernels")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["nlf"], strip_root=True)
        get(self, **sources["optmath"], strip_root=True, destination=self._optmath_folder)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Upstream expects OptMathKernels as a sibling checkout and would otherwise
        # fail configure, or with AUTO_CLONE_DEPS clone latest main at build time.
        tc.cache_variables["OPTMATH_DIR"] = self._optmath_folder.replace("\\", "/")
        tc.cache_variables["AUTO_CLONE_DEPS"] = False
        # Eigen comes from Conan; never let either project FetchContent a copy.
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True

        # The venv target pip-installs plotting requirements from PyPI.
        tc.cache_variables["NLF_BUILD_PYTHON_VENV"] = False
        # -march=native would tie the binary package to the build machine's CPU.
        tc.cache_variables["NLF_ENABLE_NATIVE_ARCH"] = False

        # GPU backends are auto-detected upstream (nvcc, Vulkan SDK). Turn them off so
        # the package does not depend on whatever happens to be on the build machine.
        tc.cache_variables["CMAKE_CUDA_COMPILER"] = ""
        tc.cache_variables["NLF_ENABLE_VULKAN"] = False

        # OpenMP is found opportunistically by both projects; make it explicit.
        tc.cache_variables["ENABLE_OPENMP"] = bool(self.options.with_openmp)
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = not self.options.with_openmp

        # OptMathKernels' own tests FetchContent GoogleTest; examples are not needed.
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_BENCHMARKS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # The benchmark driver is the only executable upstream installs.
        rmdir(self, os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "nlf")
        self.cpp_info.set_property("cmake_target_name", "nlf::nlf")

        # Upstream's headers include each other unqualified ("FilterMath.h") against a
        # flat include/nlf root, while <nlf/UKF.h> and <optmath/...> resolve off include.
        self.cpp_info.includedirs = ["include", os.path.join("include", "nlf")]
        # rbpf_core calls nothing in OptMathKernels, but the headers do.
        self.cpp_info.libs = ["rbpf_core", "OptMathKernels"]

        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]

        if self.options.with_openmp:
            openmp_flags = []
            if self.settings.compiler in ("gcc", "clang"):
                openmp_flags = ["-fopenmp"]
            elif self.settings.compiler == "apple-clang":
                openmp_flags = ["-Xpreprocessor", "-fopenmp"]
            elif self.settings.compiler == "msvc":
                openmp_flags = ["-openmp"]
            self.cpp_info.cflags += openmp_flags
            self.cpp_info.cxxflags += openmp_flags
            self.cpp_info.sharedlinkflags += openmp_flags
            self.cpp_info.exelinkflags += openmp_flags
