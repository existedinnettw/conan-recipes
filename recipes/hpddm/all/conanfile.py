import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class HpddmConan(ConanFile):
    name = "hpddm"
    description = (
        "HPDDM: high-performance framework for domain decomposition methods "
        "(Schwarz, FETI, BDD) and block/recycling Krylov solvers"
    )
    license = "LGPL-3.0-or-later"
    url = "https://github.com/hpddm/hpddm"
    homepage = "https://github.com/hpddm/hpddm"
    topics = ("domain-decomposition", "krylov", "gmres", "linear-solver", "hpc", "mpi", "header-only")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        # As every MPI recipe here: Conan Center's static Open MPI does not link
        # (libopen-pal.a misses the libevent symbols of its bundled PMIx).
        self.options["openmpi"].shared = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # HPDDM.hpp includes <mpi.h>, and the solvers take MPI communicators. Upstream's
        # sequential mode (HPDDM_MPI=0) does not compile in 2.4.1.
        self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        # The headers declare the BLAS/LAPACK routines themselves (Fortran symbols, plus
        # OpenBLAS's cblas_?axpby with HPDDM_OPENBLAS) and call them inline, so consumers
        # link them.
        self.requires("openblas/[>=0.3.24 <1]", transitive_libs=True)

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)
        if not self.dependencies["openblas"].options.build_lapack:
            raise ConanInvalidConfiguration(f"{self.ref} requires '-o openblas/*:build_lapack=True'")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "hpddm")
        self.cpp_info.set_property("cmake_target_name", "hpddm::hpddm")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # OpenBLAS is the BLAS here: use its cblas_?axpby extensions.
        self.cpp_info.defines = ["HPDDM_OPENBLAS=1"]
        # Only the MPI C component: the openmpi package as a whole also carries
        # libompitrace, whose PMPI wrappers print a trace line for every MPI call.
        self.cpp_info.requires = ["openblas::openblas_component", "openmpi::ompi-c"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
