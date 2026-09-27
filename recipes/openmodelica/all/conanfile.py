import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, load, replace_in_file, rmdir, save


class OpenModelicaConan(ConanFile):
    """OpenModelica compiler (omc), used to turn Modelica models into FMUs.

    omc is a build-machine tool, so consume it as::

        def build_requirements(self):
            self.tool_requires("openmodelica/1.27.1")

        def generate(self):
            deps = CMakeDeps(self)
            deps.build_context_activated = ["openmodelica"]
            deps.build_context_build_modules = ["openmodelica"]
            deps.generate()

    and in CMake::

        find_package(OpenModelica REQUIRED)
        openmodelica_add_fmu(my_plant MODEL Plant.Motor SOURCES Plant.mo LIBRARIES Modelica)

    Exporting an FMU makes omc configure and compile the FMU's C sources with the
    ``cmake`` and C compiler of the consuming build.
    """

    name = "openmodelica"
    description = "OpenModelica compiler (omc) for Modelica models, with FMI 2.0/3.0 FMU export"
    license = "OSMC-PL-1.8"
    url = "https://github.com/OpenModelica/OpenModelica"
    homepage = "https://openmodelica.org"
    topics = ("modelica", "fmi", "fmu", "simulation", "compiler", "modeling")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        # Bring the Modelica Standard Library, which almost every model uses, into the
        # environment omc runs in.
        "with_msl": [True, False],
    }
    default_options = {
        "with_msl": True,
        "modelica-standard-library/*:modelica_services": "openmodelica",
        # omc links it statically, and it also stands in for the "lapack" and "blas"
        # libraries that generated simulation code links to (see package()).
        "openblas/*:shared": False,
        "openblas/*:build_lapack": True,
    }

    @property
    def _openblas_archive(self):
        openblas = self.dependencies["openblas"].cpp_info.aggregated_components()
        return next(os.path.join(d, "libopenblas.a") for d in openblas.libdirs
                    if os.path.isfile(os.path.join(d, "libopenblas.a")))

    def validate(self):
        check_min_cppstd(self, 17)
        # OpenModelica's CMake build supports MSYS2/UCRT64 on Windows, not MSVC.
        if self.settings.os not in ("Linux", "FreeBSD"):
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux and FreeBSD")
        if not self.dependencies["openblas"].options.build_lapack:
            raise ConanInvalidConfiguration(f"{self.ref} requires '-o openblas/*:build_lapack=True'")
        if self.options.with_msl and \
                self.dependencies["modelica-standard-library"].options.modelica_services != "openmodelica":
            raise ConanInvalidConfiguration(
                f"{self.ref} requires '-o modelica-standard-library/*:modelica_services=openmodelica'")

    def requirements(self):
        # Libraries only omc itself links; none of them reach a consumer's link line.
        # The 3rdParty libraries generated simulation code links (sundials, SuiteSparse,
        # cminpack, lis, zlib, the gc, ...) stay bundled: omc hands them to that
        # compilation from its own library directory.
        self.requires("libcurl/[>=7.78 <9]", visible=False)
        self.requires("libffi/[>=3.4 <4]", visible=False)
        self.requires("metis/5.2.1", visible=False)
        self.requires("openblas/[>=0.3.24 <1]", visible=False)
        self.requires("util-linux-libuuid/[>=2.39 <3]", visible=False)
        self.requires("zeromq/4.3.5", visible=False)
        if self.options.with_msl:
            # Data read by omc when it runs; its environment sets OPENMODELICALIBRARY.
            self.requires("modelica-standard-library/4.1.0", run=True, headers=False, libs=False)

    def build_requirements(self):
        # The ANTLR 3 parser generator, used to generate the Modelica parser, is a Java program.
        self.tool_requires("openjdk/21.0.2")

    def export_sources(self):
        copy(self, "cmake/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Qt clients (OMEdit, OMShell, ...); they also bring OMSimulator, which has its
        # own recipe.
        tc.cache_variables["OM_ENABLE_GUI_CLIENTS"] = False
        tc.cache_variables["OM_USE_CCACHE"] = False
        # Fortran is only needed by the Ipopt based dynamic optimization runtimes.
        tc.cache_variables["OM_OMC_ENABLE_FORTRAN"] = False
        tc.cache_variables["OM_OMC_ENABLE_MOO"] = False
        tc.cache_variables["OM_OMC_ENABLE_OPTIMIZATION"] = False
        # The C++ simulation runtime (--simCodeTarget=Cpp) needs Boost; FMU export uses
        # the C runtime.
        tc.cache_variables["OM_OMC_ENABLE_CPP_RUNTIME"] = False
        # The Conan targets are found in OMCompiler/3rdParty and used from other directories.
        tc.cache_variables["CMAKE_FIND_PACKAGE_TARGETS_GLOBAL"] = True
        tc.cache_variables["BLA_VENDOR"] = "OpenBLAS"
        tc.cache_variables["BLA_STATIC"] = True
        # The static openblas needs libm and pthreads, which FindBLAS/FindLAPACK leave out
        # of their link checks (and of BLAS_LIBRARIES). Hand them a GNU ld linker script
        # that adds both, through the cache entries their find_library() calls use.
        script = os.path.join(self.generators_folder, "openblas", "libopenblas.a")
        save(self, script, f"INPUT({self._openblas_archive} -lm -lpthread)\n")
        tc.cache_variables["BLAS_openblas_LIBRARY"] = script
        tc.cache_variables["LAPACK_openblas_LIBRARY"] = script
        tc.cache_variables["BUILD_TESTING"] = False
        tc.generate()

    def _patch_sources(self):
        third_party = os.path.join(self.source_folder, "OMCompiler", "3rdParty", "CMakeLists.txt")
        replace_in_file(self, third_party,
                        """option(OM_USE_SYSTEM_LIBFFI "Use system libffi" OFF)
if (OM_USE_SYSTEM_LIBFFI)
  find_package(LibFFI MODULE REQUIRED)
  add_library(ffi INTERFACE)
  target_include_directories(ffi INTERFACE ${LIBFFI_INCLUDE_DIRS})
  target_link_libraries(ffi INTERFACE ${LIBFFI_LIBRARIES})
else ()""",
                        """option(OM_USE_SYSTEM_LIBFFI "Use system libffi" ON)
if (OM_USE_SYSTEM_LIBFFI)
  find_package(libffi REQUIRED CONFIG)
  add_library(ffi INTERFACE)
  target_link_libraries(ffi INTERFACE libffi::libffi)
else ()""")
        replace_in_file(self, third_party,
                        """set (ZMQ_BUILD_TESTS OFF CACHE BOOL "Build the tests for ZeroMQ")
set (ZMQ_BUILD_STATIC ON CACHE BOOL "Whether or not to build the static object")
set (ZMQ_BUILD_SHARED OFF CACHE BOOL "Whether or not to build the shared object")
omc_add_subdirectory(libzmq)
""",
                        "find_package(ZeroMQ REQUIRED CONFIG)\n")
        replace_in_file(self, third_party,
                        """omc_add_subdirectory(metis-5.1.0)
add_library(omc::3rd::metis ALIAS metis)
target_include_directories(metis INTERFACE metis-5.1.0/include)""",
                        """find_package(metis REQUIRED CONFIG)
add_library(omc::3rd::metis ALIAS metis::metis)""")
        # simdjson is linked into the compiler runtime but not used by any source file.
        replace_in_file(self, third_party,
                        "omc_add_subdirectory(simdjson)\nadd_library(omc::3rd::simdjson ALIAS simdjson)\n", "")
        # open62541 is only used by the OPC UA runtime (SimulationRuntime/opc, not added),
        # and oneTBB only by ParModelica (removed below).
        replace_in_file(self, third_party,
                        "omc_add_subdirectory(open62541)\nadd_library(omc::3rd::opcua ALIAS opcua)\n", "")
        cmake = load(self, third_party)
        begin = cmake.index("# Intel oneTBB")
        save(self, third_party, cmake[:begin] + cmake[cmake.index("# regex", begin):])

        # OMSICpp (another C++ runtime) and ParModelica (parallel Modelica) need Boost,
        # but upstream adds them whether or not the C++ runtime is enabled.
        runtimes_cmake = os.path.join(self.source_folder, "OMCompiler", "SimulationRuntime", "CMakeLists.txt")
        replace_in_file(self, runtimes_cmake, "omc_add_subdirectory(OMSICpp)\n", "")
        replace_in_file(self, runtimes_cmake, "  omc_add_subdirectory(ParModelica)\n", "")

        runtime_cmake = os.path.join(self.source_folder, "OMCompiler", "Compiler", "runtime", "CMakeLists.txt")
        replace_in_file(self, runtime_cmake, "target_link_libraries(omcruntime PUBLIC omc::3rd::simdjson)\n", "")
        # A bare find_library() finds libuuid but not its headers.
        replace_in_file(self, runtime_cmake,
                        "  find_library(UUID_LIB NAMES uuid REQUIRED)",
                        "  find_package(libuuid REQUIRED CONFIG)\n  set(UUID_LIB libuuid::libuuid)")
        # Link flags omc hands to the compilation of generated simulation code. Fortran is
        # disabled, and openblas was built with its C LAPACK, so there is no libgfortran.
        replace_in_file(self, runtime_cmake,
                        """  set(RT_LDFLAGS_GENERATED_CODE_SIM " -lSimulationRuntimeC -lOpenModelicaRuntimeC -lomcgc -lzlib -llapack -lblas -lm -ldl -lpthread -lgfortran -lstdc++ -rdynamic ")""",
                        """  set(RT_LDFLAGS_GENERATED_CODE_SIM " -lSimulationRuntimeC -lOpenModelicaRuntimeC -lomcgc -lzlib -llapack -lblas -lm -ldl -lpthread -lstdc++ -rdynamic ")""")
        replace_in_file(self, runtime_cmake,
                        """  set(RT_LDFLAGS_GENERATED_CODE_SOURCE_FMU_STATIC "-Wl,-Bstatic -lSimulationRuntimeFMI -Wl,-Bdynamic -llapack -lblas -lm -ldl -lpthread -lgfortran -lstdc++ -rdynamic ")""",
                        """  set(RT_LDFLAGS_GENERATED_CODE_SOURCE_FMU_STATIC "-Wl,-Bstatic -lSimulationRuntimeFMI -Wl,-Bdynamic -llapack -lblas -lm -ldl -lpthread -lstdc++ -rdynamic ")""")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _omc_libdir(self):
        # <prefix>/lib/<multiarch triple>/omc; the triple is empty on non-Debian systems.
        found = glob.glob(os.path.join(self.package_folder, "lib", "**", "omc", "libOpenModelicaRuntimeC*"),
                          recursive=True)
        if not found:
            raise ConanException("Could not find the omc library directory in the package")
        return os.path.dirname(found[0])

    def package(self):
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "OSMC-License.txt", src=self.source_folder, dst=licenses)
        cmake = CMake(self)
        cmake.install()
        # Bundled 3rdParty projects install their own CMake configs and docs; keep only
        # their license texts.
        copy(self, "FMILIB_License.txt", src=os.path.join(self.package_folder, "doc"), dst=licenses)
        for folder in ("doc", os.path.join("share", "doc"), os.path.join("share", "cmake"),
                       os.path.join("share", "cminpack")):
            rmdir(self, os.path.join(self.package_folder, folder))

        # Generated simulation code, and MSL functions annotated with Library="lapack",
        # link -llapack -lblas from omc's own library directory first. Point both at the
        # static openblas, so exported FMUs do not depend on the system's LAPACK.
        omc_libdir = self._omc_libdir
        rmdir(self, os.path.join(omc_libdir, "cmake"))
        for name in ("liblapack.a", "libblas.a"):
            shutil.copy2(self._openblas_archive, os.path.join(omc_libdir, name))
        copy(self, "*", src=os.path.join(self.dependencies["openblas"].package_folder, "licenses"),
             dst=os.path.join(licenses, "openblas"))

        copy(self, "OpenModelicaFMU.cmake", src=os.path.join(self.export_sources_folder, "cmake"),
             dst=os.path.join(self.package_folder, self._cmake_module_dir))

    @property
    def _cmake_module_dir(self):
        return os.path.join("lib", "cmake", "openmodelica")

    def package_info(self):
        # Nothing to link: omc and its runtime are used through the omc executable.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        self.cpp_info.set_property("cmake_file_name", "OpenModelica")
        self.cpp_info.set_property("cmake_target_name", "OpenModelica::OpenModelica")
        self.cpp_info.builddirs = [self._cmake_module_dir]
        self.cpp_info.set_property("cmake_build_modules",
                                   [os.path.join(self._cmake_module_dir, "OpenModelicaFMU.cmake")])

        self.conf_info.define_path("user.openmodelica:omc", os.path.join(self.package_folder, "bin", "omc"))
