import json
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rm, rmdir, save
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.0"


class ChronoConan(ConanFile):
    name = "chrono"
    description = "Project Chrono: a C++ library for multiphysics and multibody dynamics simulation"
    # Plus MPL-2.0 for the Spectra headers compiled into Chrono::Modal.
    license = ("BSD-3-Clause", "MPL-2.0")
    url = "https://github.com/projectchrono/chrono"
    homepage = "https://projectchrono.org"
    topics = ("multibody", "dynamics", "physics", "simulation", "vehicle", "fea", "robotics")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
        # Upstream's default probes the build machine and compiles with -march=native.
        "with_simd": [True, False],
        "with_vehicle": [True, False],
        "with_vehicle_models": [True, False],
        "with_robot_models": [True, False],
        "with_postprocess": [True, False],
        "with_modal": [True, False],
        "with_peridynamics": [True, False],
        "with_parsers": [True, False],
        "with_fmi": [True, False],
        # data/ (meshes, textures, vehicle and robot JSON files, ~1.2 GB) that demos
        # and the vehicle/robot models load at run time through SetChronoDataPath().
        "with_data": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": True,
        "with_simd": False,
        "with_vehicle": True,
        "with_vehicle_models": True,
        "with_robot_models": True,
        "with_postprocess": True,
        "with_modal": True,
        "with_peridynamics": True,
        "with_parsers": True,
        "with_fmi": False,
        "with_data": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        # Apple Clang has no OpenMP runtime of its own.
        if self.settings.compiler == "apple-clang":
            self.options.with_openmp = False

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_vehicle:
            del self.options.with_vehicle_models

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Chrono's headers expose Eigen types.
        self.requires("eigen/3.4.0", transitive_headers=True)
        if self.options.with_openmp and self.settings.compiler == "apple-clang":
            self.requires("llvm-openmp/20.1.6", transitive_headers=True, transitive_libs=True)
        if self.options.with_parsers:
            self.requires("yaml-cpp/0.8.0", transitive_headers=True, transitive_libs=True)
            self.requires("urdfdom/4.0.0", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["chrono"], strip_root=True)
        get(self, **self.conan_data["sources"][self.version]["fmu-forge"], strip_root=True,
            destination=os.path.join(self.source_folder, "src", "chrono_thirdparty", "fmu-forge"))
        get(self, **self.conan_data["sources"][self.version]["spectra"], strip_root=True,
            destination=os.path.join(self.source_folder, "spectra"))

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_DEMOS"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_BENCHMARKING"] = False
        tc.cache_variables["CH_USE_SIMD"] = self.options.with_simd
        if not self.options.with_openmp:
            tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = True
        if self.settings.os == "Windows" and self.settings.get_safe("compiler.runtime"):
            # msvc and clang-cl alike.
            tc.cache_variables["CH_USE_MSVC_STATIC_RUNTIME"] = self.settings.compiler.runtime == "static"
        # Only the GPU, MPI and HDF5 modules use these; keep whatever the build machine
        # happens to have out of the build.
        tc.cache_variables["CMAKE_CUDA_COMPILER"] = ""
        for package in ("Thrust", "MPI", "HDF5", "Python3", "ROS2"):
            tc.cache_variables[f"CMAKE_DISABLE_FIND_PACKAGE_{package}"] = True

        tc.cache_variables["CH_ENABLE_MODULE_VEHICLE"] = self.options.with_vehicle
        tc.cache_variables["CH_ENABLE_MODULE_VEHICLE_MODELS"] = bool(self.options.get_safe("with_vehicle_models"))
        # Co-simulation needs MPI; the vehicle FMUs are example programs.
        tc.cache_variables["CH_ENABLE_MODULE_VEHICLE_COSIM"] = False
        tc.cache_variables["CH_ENABLE_MODULE_VEHICLE_FMI"] = False
        tc.cache_variables["CH_ENABLE_MODULE_POSTPROCESS"] = self.options.with_postprocess
        tc.cache_variables["CH_ENABLE_MODULE_MODAL"] = self.options.with_modal
        tc.cache_variables["spectra_INCLUDE_DIR"] = os.path.join(self.source_folder, "spectra", "include").replace("\\", "/")
        tc.cache_variables["CH_ENABLE_MODULE_PERIDYNAMICS"] = self.options.with_peridynamics
        tc.cache_variables["CH_ENABLE_MODULE_PARSERS"] = self.options.with_parsers
        tc.cache_variables["CH_ENABLE_MODULE_FMI"] = self.options.with_fmi
        if self.options.with_fmi:
            tc.cache_variables["CONAN_FMI2_PLATFORM"], tc.cache_variables["CONAN_FMI3_PLATFORM"] = self._fmi_platforms
        # FMU export builds FMUs with their own FetchContent'ed sources.
        tc.cache_variables["FMU_EXPORT_SUPPORT"] = False
        tc.generate()

    def _patch_sources(self):
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        # The data folder is copied into the build tree at configure time and installed
        # as a whole; the templates and the Blender importer are not part of the library.
        replace_in_file(self, cmakelists,
                        "file(COPY ${CMAKE_SOURCE_DIR}/data/ DESTINATION ${CH_BUILD_DATA})", "")
        if not self.options.with_data:
            replace_in_file(self, cmakelists,
                            "install(DIRECTORY ${CMAKE_SOURCE_DIR}/data/ DESTINATION ${CH_INSTALL_DATA})", "")
        replace_in_file(self, cmakelists,
                        'install(DIRECTORY ${CMAKE_SOURCE_DIR}/src/importer_blender/ DESTINATION "importer_blender")',
                        "")

        # Chrono::Models builds the robot models unconditionally.
        if not self.options.with_robot_models:
            replace_in_file(self, os.path.join(self.source_folder, "src", "chrono_models", "CMakeLists.txt"),
                            "add_subdirectory(robot)", "")

        # Upstream names the FMI 3 platform x86 or x86_64 after the pointer size alone,
        # whatever the architecture.
        fmi = os.path.join(self.source_folder, "src", "chrono_fmi", "CMakeLists.txt")
        replace_in_file(self, fmi, "set(FMI2_PLATFORM ${FMI2_SYS}${FMI2_ARCH})", "set(FMI2_PLATFORM ${CONAN_FMI2_PLATFORM})")
        replace_in_file(self, fmi, "set(FMI3_PLATFORM ${FMI3_ARCH}-${FMI3_SYS})", "set(FMI3_PLATFORM ${CONAN_FMI3_PLATFORM})")

        # Record what the OpenMP and SIMD detection settled on: Chrono_core passes those
        # flags on to its consumers, and package_info() has to do the same.
        save(self, os.path.join(self.source_folder, "src", "chrono", "CMakeLists.txt"), textwrap.dedent("""
            file(WRITE "${CMAKE_BINARY_DIR}/conan_core_usage.json"
                 "{\\"openmp\\": \\"${CH_ENABLE_OPENMP}\\", \\"openmp_flags\\": \\"${OpenMP_CXX_FLAGS}\\", \\"simd_flags\\": \\"${SIMD_FLAGS}\\"}")
            """), append=True)

        # Copy-paste slip upstream: no Chrono::Peridynamics header gets installed.
        replace_in_file(self, os.path.join(self.source_folder, "src", "chrono_peridynamics", "CMakeLists.txt"),
                        "install(FILES ${Chrono_PardisoMKL_HEADERS}", "install(FILES ${Chrono_PERIDYNAMICS_HEADERS}")

        # ChGnuPlot.h runs the gnuplot program at run time; do not make that depend on
        # whether the build machine has it.
        replace_in_file(self, os.path.join(self.source_folder, "src", "chrono_postprocess", "CMakeLists.txt"),
                        "find_package(Gnuplot QUIET)", "set(GNUPLOT_FOUND TRUE)")

        parsers = os.path.join(self.source_folder, "src", "chrono_parsers", "CMakeLists.txt")
        # Use Conan's yaml-cpp instead of building and installing the bundled copy.
        replace_in_file(self, parsers, textwrap.dedent("""\
            FetchContent_Declare(
                  yaml-cpp
                  SOURCE_DIR "${CMAKE_SOURCE_DIR}/src/chrono_thirdparty/yaml-cpp"
                )
                FetchContent_MakeAvailable(yaml-cpp)"""), "find_package(yaml-cpp REQUIRED CONFIG)")
        replace_in_file(self, parsers, textwrap.dedent("""\
            if (MSVC)
                  target_compile_options(yaml-cpp PUBLIC $<$<COMPILE_LANGUAGE:CXX>:/wd4251>)
                  target_compile_options(yaml-cpp PUBLIC $<$<COMPILE_LANGUAGE:CXX>:/wd4275>)
                  target_compile_options(yaml-cpp PUBLIC $<$<COMPILE_LANGUAGE:CXX>:/wd4267>)
                endif()"""), "")
        for header in ("ChParserYAML.h", "ChParserCfdYAML.h"):
            replace_in_file(self, os.path.join(self.source_folder, "src", "chrono_parsers", "yaml", header),
                            '"chrono_thirdparty/yaml-cpp/include/yaml-cpp/yaml.h"', "<yaml-cpp/yaml.h>")
        replace_in_file(self, parsers, textwrap.dedent("""\
            install(TARGETS yaml-cpp
                      EXPORT ChronoTargets"""), "install(TARGETS")
        # Conan's urdfdom is a single target and ships the urdfdom_headers itself.
        replace_in_file(self, parsers, "find_package(urdfdom_headers REQUIRED)", "set(urdfdom_headers_FOUND TRUE)")
        replace_in_file(self, parsers, "urdfdom::urdfdom_model)", "urdfdom::urdfdom)")
        replace_in_file(self, parsers, "urdfdom::urdfdom_sensor)", "urdfdom::urdfdom)")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        usage = self._read_core_usage(self.build_folder)
        if self.options.with_openmp and self.settings.compiler != "apple-clang" and not usage["openmp"]:
            raise ConanException(f"{self.ref}: CMake found no OpenMP for this compiler; use -o {self.name}/*:with_openmp=False")
        cmake.build()

    @staticmethod
    def _read_core_usage(folder):
        """OpenMP and SIMD flags that the configure step settled on (conan_core_usage.json)."""
        with open(os.path.join(folder, "conan_core_usage.json"), encoding="utf-8") as f:
            usage = json.load(f)
        return {
            "openmp": usage["openmp"].upper() in ("1", "ON", "TRUE", "YES", "Y"),
            "openmp_flags": [flag for flag in usage["openmp_flags"].split(";") if flag],
            "simd_flags": [flag for flag in usage["simd_flags"].split(";") if flag],
        }

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.options.with_modal:
            copy(self, "LICENSE", src=os.path.join(self.source_folder, "spectra"),
                 dst=os.path.join(self.package_folder, "licenses", "spectra"))
        if self.options.with_fmi:
            copy(self, "LICENSE", src=os.path.join(self.source_folder, "src", "chrono_thirdparty", "fmu-forge"),
                 dst=os.path.join(self.package_folder, "licenses", "fmu-forge"))
        cmake = CMake(self)
        cmake.install()
        for folder in ("cmake", os.path.join("lib", "cmake"), "template_project",
                       os.path.join("share", "chrono", "template_project")):
            rmdir(self, os.path.join(self.package_folder, folder))
        rm(self, "*.pdb", self.package_folder, recursive=True)
        copy(self, "conan_core_usage.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib", "chrono"))
        # Copy of the bundled yaml-cpp, which the build now takes from Conan.
        rmdir(self, os.path.join(self.package_folder, "include", "chrono_thirdparty", "yaml-cpp"))
        # run_chrono (Chrono::Parsers' YAML model runner) is installed with the demos.
        if self.settings.os != "Windows":
            copy(self, "run_chrono", src=os.path.join(self.package_folder, "share", "chrono", "bin"),
                 dst=os.path.join(self.package_folder, "bin"))
            rmdir(self, os.path.join(self.package_folder, "share", "chrono", "bin"))
            if not self.options.with_data:
                rmdir(self, os.path.join(self.package_folder, "share"))
        if self.options.with_data:
            save(self, os.path.join(self.package_folder, self._module_file_rel_path), textwrap.dedent(f"""\
                # Mirrors the data variables of upstream's ChronoConfig.cmake.
                set(CHRONO_DATA_DIR "${{CMAKE_CURRENT_LIST_DIR}}/{self._data_rel_from_module}/")
                set(CHRONO_VEHICLE_DATA_DIR "${{CHRONO_DATA_DIR}}vehicle/")
            """))

    @property
    def _msvc_like(self):
        """What upstream's CMake sees as MSVC: msvc itself, and clang-cl."""
        return is_msvc(self) or (self.settings.os == "Windows" and bool(self.settings.get_safe("compiler.runtime")))

    @property
    def _fmi_platforms(self):
        """FMI 2 and FMI 3 platform names of the target (the FMU binaries/ subfolder)."""
        fmi2_os, fmi3_os = {"Windows": ("win", "windows"), "Macos": ("darwin", "darwin")}.get(
            str(self.settings.os), ("linux", "linux"))
        arch = str(self.settings.arch)
        if arch.startswith(("armv8", "armv9", "arm64")) and arch != "armv8_32":
            fmi3_arch = "aarch64"
        elif arch.startswith("arm"):
            fmi3_arch = "aarch32"
        else:
            fmi3_arch = {"ppc64le": "ppc64"}.get(arch, arch)
        bits = "64" if fmi3_arch.endswith("64") or arch in ("s390x", "sparcv9", "mips64") else "32"
        return f"{fmi2_os}{bits}", f"{fmi3_arch}-{fmi3_os}"

    @property
    def _data_rel_path(self):
        return "data" if self.settings.os == "Windows" else os.path.join("share", "chrono", "data")

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", "conan-official-chrono-variables.cmake")

    @property
    def _data_rel_from_module(self):
        return "../../" + self._data_rel_path.replace(os.sep, "/")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Chrono")
        self.cpp_info.set_property("cmake_target_name", "Chrono::Chrono")
        if self.options.with_data:
            self.cpp_info.set_property("cmake_build_modules", [self._module_file_rel_path])
            self.cpp_info.resdirs = [self._data_rel_path]

        postfix = "_d" if self.settings.build_type == "Debug" else ""

        def _component(name, lib, requires, debug_postfix=True):
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", f"Chrono::{name}")
            component.libs = [lib + (postfix if debug_postfix else "")]
            component.requires = requires
            if not self.options.shared:
                component.defines.append("CH_STATIC")
            return component

        core = _component("core", "Chrono_core", ["eigen::eigen"])
        core.includedirs = [
            "include",
            os.path.join("include", "chrono", "collision", "bullet"),
            os.path.join("include", "chrono", "collision", "gimpact"),
            os.path.join("include", "chrono_thirdparty", "HACD"),
            os.path.join("include", "chrono_thirdparty", "HACDv2"),
        ]
        core.defines.append("CH_IGNORE_DEPRECATED")
        if self._msvc_like:
            core.defines.extend(["_ENABLE_EXTENDED_ALIGNED_STORAGE", "_CRT_SECURE_NO_DEPRECATE",
                                 "_SCL_SECURE_NO_DEPRECATE", "NOMINMAX"])
            core.cxxflags.extend(["/Zc:__cplusplus", "/EHsc"])
            core.system_libs.append("ws2_32")
        usage = self._read_core_usage(os.path.join(self.package_folder, "lib", "chrono"))
        if self.options.with_openmp and self.settings.compiler == "apple-clang":
            core.requires.append("llvm-openmp::llvm-openmp")
        elif self.options.with_openmp:
            # The flags CMake's FindOpenMP found for this compiler (-fopenmp, /openmp, ...).
            core.cxxflags.extend(usage["openmp_flags"])
            if not self._msvc_like:
                core.sharedlinkflags.extend(usage["openmp_flags"])
                core.exelinkflags.extend(usage["openmp_flags"])
        else:
            core.defines.append("EIGEN_DONT_PARALLELIZE")
        if self.settings.os in ("Linux", "FreeBSD"):
            core.system_libs.extend(["pthread", "m", "dl"])
        if self.options.with_simd:
            core.cxxflags.extend(usage["simd_flags"])

        if self.options.with_vehicle:
            _component("vehicle", "Chrono_vehicle", ["core"])
            if self.options.with_vehicle_models:
                _component("vehicle_models", "ChronoModels_vehicle", ["core", "vehicle"])
        if self.options.with_robot_models:
            _component("robot_models", "ChronoModels_robot", ["core"])
        if self.options.with_postprocess:
            _component("postprocess", "Chrono_postprocess", ["core"])
        if self.options.with_modal:
            _component("modal", "Chrono_modal", ["core"])
        if self.options.with_peridynamics:
            # The only library upstream gives no debug postfix.
            _component("peridynamics", "Chrono_peridynamics", ["core"], debug_postfix=False)
        if self.options.with_parsers:
            parsers = ["core", "yaml-cpp::yaml-cpp", "urdfdom::urdfdom"]
            if self.options.with_vehicle:
                parsers.append("vehicle")
            _component("parsers", "Chrono_parsers", parsers)
        if self.options.with_fmi:
            fmi = _component("fmi", "Chrono_fmi", ["core"])
            fmi.includedirs = ["include", os.path.join("include", "chrono_thirdparty", "fmu-forge")]
            fmi2_platform, fmi3_platform = self._fmi_platforms
            fmi.defines.extend([
                f'FMI2_PLATFORM="{fmi2_platform}"',
                f'FMI3_PLATFORM="{fmi3_platform}"',
                'SHARED_LIBRARY_SUFFIX="{}"'.format(
                    {"Windows": ".dll", "Macos": ".dylib"}.get(str(self.settings.os), ".so")),
            ])
            if self.settings.os in ("Linux", "FreeBSD"):
                fmi.system_libs.append("dl")
