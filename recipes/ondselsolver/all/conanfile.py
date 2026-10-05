import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir

required_conan_version = ">=2.0"


class OndselSolverConan(ConanFile):
    name = "ondselsolver"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/FreeCAD/OndselSolver"
    description = "Assembly constraint and multibody dynamics solver used by the FreeCAD Assembly workbench"
    topics = ("freecad", "assembly", "constraints", "multibody-dynamics", "kinematics", "cad")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 17)
        # The library has no export macros, so a DLL would export nothing.
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} can only be built as a static library on Windows")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Upstream picks shared on Unix and static elsewhere; follow BUILD_SHARED_LIBS instead.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "if( UNIX )", "if( BUILD_SHARED_LIBS )")
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "ELSEIF ( APPLE )\n    set( ONDSELSOLVER_BUILD_SHARED ON )\n", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ONDSELSOLVER_BUILD_TESTS"] = False
        tc.cache_variables["ONDSELSOLVER_BUILD_EXE"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # FreeCAD finds it with pkg-config and includes <OndselSolver/...>.
        self.cpp_info.set_property("pkg_config_name", "OndselSolver")
        self.cpp_info.set_property("cmake_file_name", "OndselSolver")
        self.cpp_info.set_property("cmake_target_name", "OndselSolver::OndselSolver")
        self.cpp_info.libs = ["OndselSolver"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
        elif self.settings.os == "Windows":
            self.cpp_info.defines = ["_USE_MATH_DEFINES"]
