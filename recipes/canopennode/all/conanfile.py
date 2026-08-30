import os

from conan import ConanFile
from conan.tools.files import copy, get, save


class CANopenNodeConan(ConanFile):
    name = "canopennode"
    license = "Apache-2.0"
    url = "https://github.com/CANopenNode/CANopenNode"
    homepage = "https://canopennode.github.io"
    description = "CANopen protocol stack written in ANSI C"
    topics = ("canopen", "can", "embedded", "industrial-automation")
    package_type = "header-library"

    no_copy_source = True

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "*.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "*.c",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "src"),
            excludes=("example/*",),
        )
        copy(
            self,
            "CO_driver_blank.c",
            src=os.path.join(self.source_folder, "example"),
            dst=os.path.join(self.package_folder, "src", "example"),
        )
        copy(
            self,
            "DS301_profile.eds",
            src=os.path.join(self.source_folder, "example"),
            dst=os.path.join(self.package_folder, "res"),
        )
        save(
            self,
            os.path.join(self.package_folder, "cmake", "CANopenNodeSources.cmake"),
            self._cmake_sources_module(),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include", os.path.join("include", "301")]
        self.cpp_info.set_property("cmake_file_name", "CANopenNode")
        self.cpp_info.set_property("cmake_target_name", "CANopenNode::headers")
        self.cpp_info.set_property(
            "cmake_build_modules",
            [os.path.join("cmake", "CANopenNodeSources.cmake")],
        )
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

    @staticmethod
    def _cmake_sources_module():
        sources = (
            "301/CO_Emergency.c",
            "301/CO_fifo.c",
            "301/CO_HBconsumer.c",
            "301/CO_NMT_Heartbeat.c",
            "301/CO_Node_Guarding.c",
            "301/CO_ODinterface.c",
            "301/CO_PDO.c",
            "301/CO_SDOclient.c",
            "301/CO_SDOserver.c",
            "301/CO_SYNC.c",
            "301/CO_TIME.c",
            "301/crc16-ccitt.c",
            "303/CO_LEDs.c",
            "304/CO_GFC.c",
            "304/CO_SRDO.c",
            "305/CO_LSSmaster.c",
            "305/CO_LSSslave.c",
            "309/CO_gateway_ascii.c",
            "CANopen.c",
            "extra/CO_trace.c",
            "storage/CO_storage.c",
        )
        source_properties = "\n".join(
            f'    "${{_CANOPENNODE_PACKAGE_ROOT}}/src/{source}"' for source in sources
        )
        return f"""\
if(NOT TARGET CANopenNode::CANopenNode)
    get_filename_component(
        _CANOPENNODE_PACKAGE_ROOT
        "${{CMAKE_CURRENT_LIST_DIR}}/.."
        ABSOLUTE
    )

    add_library(CANopenNode::CANopenNode INTERFACE IMPORTED)
    set_property(
        TARGET CANopenNode::CANopenNode
        PROPERTY INTERFACE_LINK_LIBRARIES CANopenNode::headers
    )
    set_property(
        TARGET CANopenNode::CANopenNode
        PROPERTY INTERFACE_SOURCES
{source_properties}
    )

    add_library(CANopenNode::example_driver INTERFACE IMPORTED)
    set_property(
        TARGET CANopenNode::example_driver
        PROPERTY INTERFACE_LINK_LIBRARIES CANopenNode::headers
    )
    set_property(
        TARGET CANopenNode::example_driver
        PROPERTY INTERFACE_SOURCES
            "${{_CANOPENNODE_PACKAGE_ROOT}}/src/example/CO_driver_blank.c"
    )

    unset(_CANOPENNODE_PACKAGE_ROOT)
endif()
"""
