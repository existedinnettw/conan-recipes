import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"


class ParmetisConan(ConanFile):
    name = "parmetis"
    description = (
        "ParMETIS: MPI-parallel graph partitioning, adaptive repartitioning and "
        "fill-reducing ordering of sparse matrices"
    )
    # Not an open-source licence: free for education and research at non-profit
    # institutions and US government agencies, evaluation only for everyone else,
    # and no redistribution without approval. See licenses/LICENSE in the package.
    license = "LicenseRef-ParMETIS"
    url = "https://github.com/KarypisLab/ParMETIS"
    homepage = "https://github.com/KarypisLab/ParMETIS"
    topics = ("graph-partitioning", "mesh-partitioning", "sparse-matrix-ordering", "hpc", "mpi")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    exports_sources = "CMakeLists.txt"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Pure C library.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")
        # Open MPI's static archives define the MPI_* entry points as weak symbols,
        # so a shared library linking libmpi.a does not pull them in and is left
        # with undefined MPI symbols plus a partial copy of the profiling wrappers.
        self.options["openmpi"].shared = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # parmetis.h includes <mpi.h> and <metis.h>, and its idx_t/real_t are METIS'.
        self.requires("openmpi/[>=4.1 <5]", transitive_headers=True, transitive_libs=True)
        self.requires("metis/[>=5.2.1 <6]", transitive_headers=True, transitive_libs=True)
        # Used by the library code only (GKlib.h in libparmetis/parmetislib.h).
        self.requires("gklib/[>=5.1.1 <6]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                f"{self.ref} is not supported on Windows: no MPI package is available for it"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["PARMETIS_SRC_DIR"] = self.source_folder.replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, os.pardir))
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "parmetis")
        self.cpp_info.set_property("cmake_target_name", "parmetis::parmetis")
        self.cpp_info.set_property("pkg_config_name", "parmetis")
        self.cpp_info.libs = ["parmetis"]
        # Only the MPI C component: the openmpi package as a whole also carries
        # libompitrace, whose PMPI wrappers print a trace line for every MPI call.
        self.cpp_info.requires = ["openmpi::ompi-c", "metis::metis", "gklib::gklib"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
