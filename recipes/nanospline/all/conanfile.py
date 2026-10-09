import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
from conan.tools.microsoft import is_msvc


class NanosplineConan(ConanFile):
    name = "nanospline"
    description = "Header-only C++ library for Bezier, rational Bezier, B-spline and NURBS curves and patches"
    license = "MPL-2.0"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/qnzhou/nanospline"
    topics = ("spline", "nurbs", "bezier", "b-spline", "geometry", "header-only")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        # False builds upstream's static library of explicit template instantiations,
        # which saves consumers from compiling the generated code themselves.
        "header_only": [True, False],
        # Inflection, singularity and tangent matching of Bezier curves use code
        # generated with SymPy; without it they throw not_implemented_error.
        "with_sympy": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "header_only": True,
        "with_sympy": False,
        "fPIC": True,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.header_only:
            self.options.rm_safe("fPIC")
        else:
            self.package_type = "static-library"

    def requirements(self):
        self.requires("eigen/[>=3.4.0 <4]", transitive_headers=True)

    def package_id(self):
        if self.info.options.header_only:
            self.info.settings.clear()

    def validate(self):
        check_min_cppstd(self, 20)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if self.options.header_only:
            return
        tc = CMakeToolchain(self)
        tc.cache_variables["NANOSPLINE_SYMPY"] = bool(self.options.with_sympy)
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        if self.options.header_only:
            return
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.options.header_only:
            copy(self, "*.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        else:
            CMake(self).install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "nanospline")
        self.cpp_info.set_property("cmake_target_name", "nanospline::nanospline")
        if self.options.header_only:
            self.cpp_info.bindirs = []
            self.cpp_info.libdirs = []
            self.cpp_info.defines.append("NANOSPLINE_HEADER_ONLY")
        else:
            self.cpp_info.libs = ["nanospline"]
        if self.options.with_sympy:
            self.cpp_info.defines.append("NANOSPLINE_SYMPY")
        if is_msvc(self):
            self.cpp_info.defines.append("_USE_MATH_DEFINES")
            self.cpp_info.cxxflags.append("/bigobj")
