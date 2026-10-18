import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, save


class OpenPowerlinkConan(ConanFile):
    name = "openpowerlink"
    license = "BSD-3-Clause"
    url = "https://github.com/OpenAutomationTechnologies/openPOWERLINK_V2"
    homepage = "https://openpowerlink.sourceforge.net"
    description = (
        "openPOWERLINK: open source Ethernet POWERLINK protocol stack for "
        "Managing Nodes (MN) and Controlled Nodes (CN)"
    )
    topics = ("powerlink", "ethernet", "fieldbus", "industrial", "realtime", "canopen")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_mn": [True, False],
        "with_cn": [True, False],
        "with_pcap": [True, False],
        "mn_redundancy": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_mn": True,
        "with_cn": True,
        "with_pcap": False,
        "mn_redundancy": False,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")
        if not self.options.with_mn:
            self.options.rm_safe("mn_redundancy")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_pcap:
            self.requires("libpcap/1.10.5")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(
                "This recipe only builds the openPOWERLINK Linux userspace stack"
            )
        if not str(self.settings.arch).startswith(("x86", "arm")):
            raise ConanInvalidConfiguration(
                f"openPOWERLINK has no Linux port for {self.settings.arch}"
            )
        if not self.options.with_mn and not self.options.with_cn:
            raise ConanInvalidConfiguration("Enable at least one of with_mn, with_cn")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Setting CMP0043 to OLD is an error with CMake 4.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "stack", "CMakeLists.txt"),
            "    CMAKE_POLICY(SET CMP0043 OLD)\n",
            "",
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CFG_COMPILE_SHARED_LIBRARY"] = bool(self.options.shared)
        tc.cache_variables["CFG_USE_PCAP_EDRV"] = bool(self.options.with_pcap)
        tc.cache_variables["CFG_INCLUDE_MN_REDUNDANCY"] = bool(
            self.options.get_safe("mn_redundancy")
        )
        # Only the direct-link libraries (application and stack in one process).
        # The userspace-daemon, kernel-module, PCIe/Zynq and simulation variants
        # need drivers or a simulator that this recipe does not package.
        tc.cache_variables["CFG_COMPILE_LIB_MN"] = bool(self.options.with_mn)
        tc.cache_variables["CFG_COMPILE_LIB_CN"] = bool(self.options.with_cn)
        for lib in (
            "MNAPP_USERINTF", "MNAPP_KERNELINTF", "MNAPP_PCIEINTF", "MNAPP_ZYNQINTF",
            "MNDRV_PCAP", "MN_SIM",
            "CNAPP_USERINTF", "CNAPP_KERNELINTF", "CNAPP_ZYNQINTF",
            "CNDRV_PCAP", "CN_SIM",
        ):
            tc.cache_variables[f"CFG_COMPILE_LIB_{lib}"] = False
        # Upstream sets these through COMPILE_DEFINITIONS_DEBUG, which CMake >= 3.0 ignores.
        if self.settings.build_type == "Debug":
            tc.preprocessor_definitions["DEBUG"] = None
            tc.preprocessor_definitions["DEF_DEBUG_LVL"] = "0xC0000000L"
        if self.options.with_pcap:
            # Upstream expects pcap.h on the system include path and leaves linking to the app.
            inject = os.path.join(self.generators_folder, "openpowerlink_pcap.cmake")
            save(self, inject, "find_package(libpcap REQUIRED CONFIG)\nlink_libraries(libpcap::libpcap)\n")
            tc.cache_variables["CMAKE_PROJECT_openPOWERLINK_INCLUDE"] = inject.replace("\\", "/")
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="stack")
        cmake.build()

    def package(self):
        copy(self, "license.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(
            self,
            "*.h",
            os.path.join(self.source_folder, "stack", "include", "oplk"),
            os.path.join(self.package_folder, "include", "oplk"),
        )
        for pattern in ("*.a", "*.so*"):
            copy(
                self,
                pattern,
                self.build_folder,
                os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        # Applications compile the object dictionary themselves: obdcreate.c includes
        # the application's objdict.h. Ship it with the reference dictionaries.
        res = os.path.join(self.package_folder, "res", "openpowerlink")
        copy(
            self,
            "obdcreate/*",
            os.path.join(self.source_folder, "apps", "common", "src"),
            res,
        )
        for objdict in ("CiA302-4_MN", "CiA401_CN"):
            for pattern in ("*.h", "*.c"):
                copy(
                    self,
                    pattern,
                    os.path.join(self.source_folder, "apps", "common", "objdicts", objdict),
                    os.path.join(res, "objdicts", objdict),
                )
        save(
            self,
            os.path.join(self.package_folder, "lib", "cmake", "openpowerlink-vars.cmake"),
            self._cmake_vars_module(),
        )

    def _cmake_vars_module(self):
        return """\
get_filename_component(_OPLK_RES "${CMAKE_CURRENT_LIST_DIR}/../../res/openpowerlink" ABSOLUTE)
set(OPENPOWERLINK_APPS_COMMON_DIR "${_OPLK_RES}")
set(OPENPOWERLINK_OBDCREATE_SOURCES "${_OPLK_RES}/obdcreate/obdcreate.c")
set(OPENPOWERLINK_OBJDICTS_DIR "${_OPLK_RES}/objdicts")
unset(_OPLK_RES)
"""

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "openpowerlink")
        self.cpp_info.set_property(
            "cmake_build_modules", [os.path.join("lib", "cmake", "openpowerlink-vars.cmake")]
        )
        self.cpp_info.resdirs = ["res"]
        postfix = "_d" if self.settings.build_type == "Debug" else ""
        for node, enabled in (("mn", self.options.with_mn), ("cn", self.options.with_cn)):
            if not enabled:
                continue
            component = self.cpp_info.components[f"oplk{node}"]
            component.set_property("cmake_target_name", f"openpowerlink::oplk{node}")
            component.libs = [f"oplk{node}{postfix}"]
            component.system_libs = ["pthread", "rt"]
            component.resdirs = ["res"]
            component.builddirs = [os.path.join("lib", "cmake")]
            defines = ["CONFIG_KERNELSTACK_DIRECTLINK"]
            if node == "mn" and self.options.get_safe("mn_redundancy"):
                defines.append("CONFIG_INCLUDE_NMT_RMN")
            component.defines = defines
            if self.options.with_pcap:
                component.requires = ["libpcap::libpcap"]
