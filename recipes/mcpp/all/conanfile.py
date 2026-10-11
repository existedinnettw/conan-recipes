import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class McppConan(ConanFile):
    name = "mcpp"
    description = ("mcpp, a portable C/C++ preprocessor, as a library, with Open 3D Engine's patches "
                   "(which O3DE's shader builders preprocess AZSL with)")
    license = ("BSD-2-Clause", "Apache-2.0", "MIT")
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://mcpp.sourceforge.net"
    topics = ("preprocessor", "c", "c++", "o3de")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # C library
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os == "Windows":
            # Upstream (O3DE) builds Windows with nmake and its own makefile.
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux and macOS")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # The library only (libmcpp), as O3DE builds it; the mcpp executable is not built.
        tc.configure_args.append("--enable-mcpplib")
        # 2008 code: C23 (GCC 15's default) makes true/false keywords, and GCC 14 and Clang 16 made
        # these warnings errors.
        tc.extra_cflags += ["-std=gnu99", "-Wno-error=implicit-function-declaration",
                            "-Wno-error=incompatible-pointer-types"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["mcpp"]
