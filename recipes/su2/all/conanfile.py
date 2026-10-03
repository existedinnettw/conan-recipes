import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.0"


class Su2Conan(ConanFile):
    name = "su2"
    description = (
        "SU2: an open-source suite for multiphysics simulation and design, centred on "
        "compressible and incompressible CFD with adjoint-based shape optimisation"
    )
    license = "LGPL-2.1-or-later"
    url = "https://github.com/su2code/SU2"
    homepage = "https://su2code.github.io"
    topics = ("cfd", "computational-fluid-dynamics", "adjoint", "optimization", "hpc", "mpi")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_mpi": [True, False],
        "with_openmp": [True, False],
        "with_tecio": [True, False],
        "with_cgns": [True, False],
        # Builds SU2_CFD_AD (discrete adjoint, CoDiPack reverse mode) in addition.
        "with_autodiff": [True, False],
        # Builds SU2_CFD_DIRECTDIFF (CoDiPack forward mode) in addition.
        "with_directdiff": [True, False],
        # Single precision for the sparse linear algebra (preconditioners, Krylov).
        "mixed_precision": [True, False],
    }
    default_options = {
        "with_mpi": True,
        "with_openmp": False,
        "with_tecio": True,
        "with_cgns": True,
        "with_autodiff": False,
        "with_directdiff": False,
        "mixed_precision": False,
    }

    def configure(self):
        if self.options.with_mpi:
            # Shared, so that mpirun from the package and the library SU2 links agree.
            self.options["openmpi"].shared = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Header-only; SU2's own copy is a git submodule missing from the tarball.
        self.requires("eigen/[>=3.4.0 <3.5]")
        # For the HDF5 copy bundled with CGNS; otherwise Meson takes the system zlib.
        self.requires("zlib/[>=1.2.11 <2]")
        if self.options.with_mpi:
            # Parallel runs need the matching mpirun.
            self.requires("openmpi/[>=4.1 <5]", run=True)

    def build_requirements(self):
        # meson.build asks for meson_version >= 1.8.2.
        self.tool_requires("meson/[>=1.8.2 <2]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.1.0 <3]")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux and macOS")
        if self.options.with_autodiff and self.options.with_openmp:
            # Needs OpDiLib, another submodule that is not packaged here.
            raise ConanInvalidConfiguration(
                f"{self.ref} with with_autodiff=True does not support with_openmp=True"
            )

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["su2"], strip_root=True)
        # MEL is compiled in, FADO (a Python package) is installed next to the SU2
        # scripts, and CoDiPack/MeDiPack are used by the AD options; all are small.
        for name, folder in (("mel", "mel"), ("fado", "FADO"), ("codi", "codi"), ("medi", "medi")):
            get(self, **sources[name], strip_root=True,
                destination=os.path.join(self.source_folder, "externals", folder))
        # meson.build refuses to configure unless SU2's own preconfigure.py has run,
        # which would download the submodules fetched above (and meson and ninja).
        save(self, os.path.join(self.source_folder, "su2preconfig.timestamp"), "")

    def _generate_mpi_env(self):
        # Meson asks the MPI compiler wrappers (MPICC/MPICXX, else mpicc/mpic++ on
        # PATH) before it tries pkg-config, so it would take a system MPI if there is
        # one. Point it at the wrappers of the openmpi package instead; they need the
        # OPAL_* variables from the package's run environment to find their data.
        openmpi = self.dependencies["openmpi"]
        bindir = os.path.join(openmpi.package_folder, "bin")
        env = Environment()
        env.compose_env(openmpi.runenv_info)
        env.define_path("MPICC", os.path.join(bindir, "mpicc"))
        env.define_path("MPICXX", os.path.join(bindir, "mpic++"))
        # The wrappers link only -lmpi; ld resolves the libraries libmpi.so needs
        # (hwloc, libnl, ...) through LD_LIBRARY_PATH.
        libdirs = []
        for dep in self.dependencies.host.values():
            if dep.package_folder and dep.options.get_safe("shared"):
                libdirs += dep.cpp_info.aggregated_components().libdirs
        env.prepend_path("LD_LIBRARY_PATH", libdirs)
        env.vars(self, scope="build").save_script("conan_openmpi_wrappers")

    def generate(self):
        VirtualBuildEnv(self).generate()

        PkgConfigDeps(self).generate()
        if self.options.with_mpi:
            self._generate_mpi_env()

        tc = MesonToolchain(self)
        tc.project_options["with-mpi"] = "enabled" if self.options.with_mpi else "disabled"
        tc.project_options["with-omp"] = bool(self.options.with_openmp)
        tc.project_options["enable-tecio"] = bool(self.options.with_tecio)
        tc.project_options["enable-cgns"] = bool(self.options.with_cgns)
        tc.project_options["enable-autodiff"] = bool(self.options.with_autodiff)
        tc.project_options["enable-directdiff"] = bool(self.options.with_directdiff)
        tc.project_options["enable-mixedprec"] = bool(self.options.mixed_precision)
        tc.project_options["enable-normal"] = True
        tc.project_options["enable-tests"] = False
        tc.project_options["enable-pywrapper"] = False
        # Upstream defaults to -march=native, which ties the binaries to the build
        # machine's CPU.
        tc.project_options["cpu-arch"] = ""
        # Eigen comes from Conan; externals/eigen stays empty.
        tc.project_options["extra-deps"] = "eigen3"
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        for license_file in ("LICENSE.md", "COPYING"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        bindir = os.path.join(self.package_folder, "bin")
        # The SU2 Python scripts (parallel_computation.py, shape_optimization.py, ...)
        # are installed next to the executables and find them through SU2_RUN; their
        # "SU2" Python package lives there too.
        for env_info in (self.buildenv_info, self.runenv_info):
            env_info.define_path("SU2_RUN", bindir)
            env_info.prepend_path("PYTHONPATH", bindir)
