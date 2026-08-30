import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save


class CANopenLinuxConan(ConanFile):
    name = "canopenlinux"
    license = "Apache-2.0"
    url = "https://github.com/CANopenNode/CANopenLinux"
    homepage = "https://canopennode.github.io"
    description = "Linux SocketCAN driver and event interface for CANopenNode"
    topics = ("canopen", "socketcan", "can", "linux", "industrial-automation")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def requirements(self):
        self.requires("canopennode/4.0.378", transitive_headers=True)

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("CANopenLinux requires a Linux target")

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
            keep_path=False,
        )
        for source in self._sources:
            copy(
                self,
                source,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "src"),
                keep_path=False,
            )
        save(
            self,
            os.path.join(self.package_folder, "cmake", "CANopenLinuxSources.cmake"),
            self._cmake_sources_module(),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CANopenLinux")
        self.cpp_info.set_property("cmake_target_name", "CANopenLinux::headers")
        self.cpp_info.set_property(
            "cmake_build_modules",
            [os.path.join("cmake", "CANopenLinuxSources.cmake")],
        )
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

    @property
    def _sources(self):
        return (
            "CO_driver.c",
            "CO_epoll_interface.c",
            "CO_error.c",
            "CO_storageLinux.c",
        )

    def _cmake_sources_module(self):
        source_properties = "\n".join(
            f'    "${{_CANOPENLINUX_PACKAGE_ROOT}}/src/{source}"'
            for source in self._sources
        )
        return f"""\
if(NOT TARGET CANopenLinux::CANopenLinux)
    find_package(Threads REQUIRED)
    get_filename_component(
        _CANOPENLINUX_PACKAGE_ROOT
        "${{CMAKE_CURRENT_LIST_DIR}}/.."
        ABSOLUTE
    )

    add_library(CANopenLinux::CANopenLinux INTERFACE IMPORTED)
    set_property(
        TARGET CANopenLinux::CANopenLinux
        PROPERTY INTERFACE_LINK_LIBRARIES
            CANopenLinux::headers
            CANopenNode::CANopenNode
            Threads::Threads
    )
    set_property(
        TARGET CANopenLinux::CANopenLinux
        PROPERTY INTERFACE_SOURCES
{source_properties}
    )

    unset(_CANOPENLINUX_PACKAGE_ROOT)
endif()
"""
