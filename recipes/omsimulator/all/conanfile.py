import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rm, rmdir, save


class OMSimulatorConan(ConanFile):
    name = "omsimulator"
    description = (
        "OpenModelica FMI (FMI 2.0/3.0) and SSP based co-simulation library, "
        "with the OMSimulator command line tool"
    )
    license = "OSMC-PL-1.8"
    url = "https://github.com/OpenModelica/OMSimulator"
    homepage = "https://github.com/OpenModelica/OMSimulator"
    topics = ("fmi", "fmu", "ssp", "co-simulation", "simulation", "modelica", "openmodelica")
    # Upstream also builds a static library, but installs no CMake config or pkg-config
    # file that would carry its dependencies; the shared library links them in.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.os not in ("Linux", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(f"{self.ref} is only packaged for Linux, FreeBSD and macOS")

    def requirements(self):
        # All of them are linked into libOMSimulator; none appears in its public header.
        self.requires("ctpl/0.0.2", visible=False)
        self.requires("lua/5.4.6", visible=False)
        # OpenModelica's fmi4c fork; upstream fmi4c 1.x changed the API OMSimulator uses.
        self.requires("omsimulator-fmi4c/cci.20241114", visible=False)
        self.requires("pugixml/1.14", visible=False)
        # The version the bundled copy has; newer releases changed the solver APIs.
        self.requires("sundials/5.4.0", visible=False)
        # OMSimulator hard codes the xercesc_3_2 namespace.
        self.requires("xerces-c/3.2.5", visible=False)
        self.requires("zlib/[>=1.2.11 <2]", visible=False)

    def export_sources(self):
        copy(self, "cmake/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, url=sources["url"], sha256=sources["sha256"], strip_root=True)
        # Without Git metadata upstream would report its version as "unknown".
        save(self, os.path.join(self.source_folder, "version.txt"), sources["describe"] + "\n")

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["OM_OMS_ENABLE_TESTSUITE"] = False
        # The Conan targets are found in 3rdParty/ and used from src/.
        tc.cache_variables["CMAKE_FIND_PACKAGE_TARGETS_GLOBAL"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Sphinx"] = True
        if self.settings.os in ("Linux", "FreeBSD"):
            # Keep the statically linked dependencies out of libOMSimulator's dynamic
            # symbol table, so they cannot clash with a consumer's own copies.
            tc.extra_sharedlinkflags.append("-Wl,--exclude-libs,ALL")
        tc.generate()

    def _patch_sources(self):
        copy(self, "3rdParty.cmake", src=os.path.join(self.export_sources_folder, "cmake"),
             dst=os.path.join(self.source_folder, "3rdParty"))
        os.replace(os.path.join(self.source_folder, "3rdParty", "3rdParty.cmake"),
                   os.path.join(self.source_folder, "3rdParty", "CMakeLists.txt"))
        # The "pip" directory installs setup.py into the source tree.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "add_subdirectory(src/pip)\n", "")
        # Install to lib/ rather than lib/<multiarch triple>/.
        replace_in_file(self, os.path.join(self.source_folder, "config.cmake", "OMSimulatorTopLevelSettings.cmake"),
                        'set(CMAKE_INSTALL_LIBDIR "${CMAKE_INSTALL_LIBDIR}/${CMAKE_LIBRARY_ARCHITECTURE}")', "")
        replace_in_file(self, os.path.join(self.source_folder, "src", "OMSimulatorLib", "CMakeLists.txt"),
                        "install(TARGETS OMSimulatorLib_static)", "")
        # Uses fabs(), which it only got through the header-only pugixml the bundled
        # sources compile in.
        replace_in_file(self, os.path.join(self.source_folder, "src", "OMSimulatorLib", "AlgLoop.cpp"),
                        "#include <sstream>", "#include <cmath>\n#include <sstream>")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "OSMC-License.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # A static helper for the Lua bindings; it links the shared library.
        rm(self, "*OMSimulatorLua*", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OMSimulator")
        self.cpp_info.set_property("cmake_target_name", "OMSimulator::OMSimulator")
        self.cpp_info.set_property("pkg_config_name", "OMSimulator")
        self.cpp_info.libs = ["OMSimulator"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["dl", "pthread", "m"]

        bin_dir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
