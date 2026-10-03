import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir, save

required_conan_version = ">=2.0"


class NemohConan(ConanFile):
    name = "nemoh"
    description = (
        "Nemoh: a boundary element method solver for first and second order wave loads "
        "on floating structures (added mass, radiation damping, diffraction forces, QTFs)"
    )
    license = "GPL-3.0-or-later"
    url = "https://gitlab.com/lheea/Nemoh"
    homepage = "https://lheea.gitlab.io/Nemoh"
    topics = ("bem", "boundary-element-method", "hydrodynamics", "offshore", "potential-flow", "fortran")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # solver, postProc and the QTF programs call LAPACK (and BLAS through it).
        self.requires("openblas/[>=0.3.24 <1]")

    def package_id(self):
        # Fortran only: the C++ settings do not reach the binaries.
        self.info.settings.rm_safe("compiler.cppstd")
        self.info.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.settings.os not in ("Linux", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux, FreeBSD and macOS")
        if not self.dependencies["openblas"].options.build_lapack:
            raise ConanInvalidConfiguration(f"{self.ref} requires '-o openblas/*:build_lapack=True'")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        # Upstream passes -static-libgfortran to the compile steps only, where it has
        # no effect; link with it as intended, so the programs do not need the build
        # machine's libgfortran.
        include = os.path.join(self.generators_folder, "conan_nemoh_project_include.cmake")
        save(self, include, 'if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")\n'
                            '  add_link_options(-static-libgfortran)\n'
                            'endif()\n')
        tc.cache_variables["CMAKE_PROJECT_Nemoh_INCLUDE"] = include.replace("\\", "/")
        tc.generate()

        deps = CMakeDeps(self)
        # Upstream calls find_package(LAPACK) and links LAPACK::LAPACK. A FindLAPACK
        # module for the openblas package, in the generators folder that comes first
        # on CMAKE_MODULE_PATH, replaces CMake's, which would search the build machine.
        deps.set_property("openblas", "cmake_find_mode", "module")
        deps.set_property("openblas", "cmake_module_file_name", "LAPACK")
        deps.set_property("openblas", "cmake_module_target_name", "LAPACK::LAPACK")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Only the licence, installed as share/doc/Nemoh/copyright.
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
