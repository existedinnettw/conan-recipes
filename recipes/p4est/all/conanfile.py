import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir

required_conan_version = ">=2.0"


class P4estConan(ConanFile):
    name = "p4est"
    description = (
        "p4est: parallel adaptive mesh refinement on forests of quadtrees and octrees, "
        "with its utility library libsc"
    )
    # p4est itself is GPL; the bundled libsc is LGPL.
    license = ("GPL-2.0-or-later", "LGPL-2.1-or-later")
    url = "https://github.com/cburstedde/p4est"
    homepage = "https://www.p4est.org"
    topics = ("amr", "adaptive-mesh-refinement", "octree", "forest-of-octrees", "hpc", "mpi")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_mpi": [True, False],
        # p8est (3D) and p6est (2D x 1D columns) are compiled into libp4est.
        "with_p8est": [True, False],
        "with_p6est": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_mpi": True,
        "with_p8est": True,
        "with_p6est": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Pure C libraries.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")
        if not self.options.with_p8est:
            self.options.rm_safe("with_p6est")
        if self.options.with_mpi:
            # Open MPI's static archives define the MPI_* entry points as weak symbols,
            # so a shared library linking libmpi.a does not pull them in and is left
            # with undefined MPI symbols plus a partial copy of the profiling wrappers.
            self.options["openmpi"].shared = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_mpi:
            # sc.h includes <mpi.h>, and the p4est API takes MPI communicators.
            self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        # libsc's sc_io.c compresses with zlib; it would build its own copy otherwise.
        self.requires("zlib/[>=1.2.11 <2]")

    def validate(self):
        if self.options.with_mpi and self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} with with_mpi=True is not supported on Windows: no MPI package "
                "is available for it. Use '-o p4est/*:with_mpi=False'."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # libsc probes zlib and MPI features with check_c_source_compiles() against the
        # CMakeDeps targets, whose properties only apply in the build configuration.
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["SC_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["SC_ENABLE_MPI"] = bool(self.options.with_mpi)
        tc.cache_variables["enable_p8est"] = bool(self.options.with_p8est)
        tc.cache_variables["enable_p6est"] = bool(self.options.get_safe("with_p6est"))
        tc.cache_variables["P4EST_BUILD_TESTING"] = False
        tc.cache_variables["P4EST_BUILD_EXAMPLES"] = False
        tc.cache_variables["SC_BUILD_TESTING"] = False
        tc.cache_variables["SC_BUILD_EXAMPLES"] = False
        tc.cache_variables["SC_USE_INTERNAL_ZLIB"] = False
        tc.cache_variables["SC_USE_INTERNAL_JSON"] = False
        # libsc's JSON support is optional; keep it from finding a jansson on the build
        # machine.
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_jansson"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(
            self,
            "COPYING",
            src=os.path.join(self.source_folder, "sc"),
            dst=os.path.join(self.package_folder, "licenses", "sc"),
        )
        cmake = CMake(self)
        cmake.install()
        # Upstream's CMake and pkg-config files hard-code build machine paths;
        # CMakeDeps and PkgConfigDeps generate correct ones for consumers instead.
        for folder in (("lib", "cmake"), ("lib", "pkgconfig"), ("cmake",), ("share",)):
            rmdir(self, os.path.join(self.package_folder, *folder))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "P4EST")
        self.cpp_info.set_property("cmake_target_name", "P4EST::P4EST")

        system_libs = []
        if self.settings.os in ("Linux", "FreeBSD"):
            system_libs = ["m", "pthread"]

        sc = self.cpp_info.components["sc"]
        sc.set_property("cmake_target_name", "SC::SC")
        sc.set_property("pkg_config_name", "libsc")
        sc.libs = ["sc"]
        sc.system_libs = list(system_libs)
        # Only the MPI C component: the openmpi package as a whole also carries
        # libompitrace, whose PMPI wrappers print a trace line for every MPI call.
        sc.requires = ["zlib::zlib"]
        if self.options.with_mpi:
            sc.requires.append("openmpi::ompi-c")

        p4est = self.cpp_info.components["p4est"]
        p4est.set_property("cmake_target_name", "P4EST::p4est")
        p4est.set_property("pkg_config_name", "p4est")
        p4est.libs = ["p4est"]
        p4est.system_libs = list(system_libs)
        p4est.requires = ["sc"]
