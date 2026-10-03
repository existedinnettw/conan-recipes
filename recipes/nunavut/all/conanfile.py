import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class NunavutConan(ConanFile):
    name = "nunavut"
    license = "MIT"
    url = "https://github.com/existedinnettw/conan-recipes"
    homepage = "https://github.com/OpenCyphal/nunavut"
    description = "Generates C and C++ (de)serialization code from Cyphal DSDL definitions"
    topics = ("cyphal", "uavcan", "dsdl", "code-generator", "pydsdl")
    package_type = "application"

    # Pure Python (Jinja2 and MarkupSafe are vendored, and so is pydsdl here), so one
    # package serves every platform. It runs on the system's Python 3.10 or newer.
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["nunavut"], strip_root=True)
        for submodule in ("pydsdl", "public_regulated_data_types"):
            get(
                self,
                **sources[submodule],
                destination=os.path.join(self.source_folder, "submodules", submodule),
                strip_root=True,
            )
        apply_conandata_patches(self)

    def build(self):
        pass

    def package(self):
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE.rst", self.source_folder, licenses)
        submodules = os.path.join(self.source_folder, "submodules")
        copy(self, "LICENSE", os.path.join(submodules, "pydsdl"), os.path.join(licenses, "pydsdl"))
        copy(
            self,
            "LICENSE",
            os.path.join(submodules, "public_regulated_data_types"),
            os.path.join(licenses, "public_regulated_data_types"),
        )

        # NunavutConfig.cmake runs Nunavut from source, relative to itself: the
        # package in src/, pydsdl from submodules/pydsdl, and the uavcan namespace
        # from submodules/public_regulated_data_types.
        copy(self, "Nunavut*.cmake", self.source_folder, self.package_folder)
        copy(
            self,
            "nunavut/*",
            os.path.join(self.source_folder, "src"),
            os.path.join(self.package_folder, "src"),
            excludes=("*/__pycache__/*", "*.pyc"),
        )
        copy(
            self,
            "pydsdl/*",
            os.path.join(submodules, "pydsdl"),
            os.path.join(self.package_folder, "submodules", "pydsdl"),
            excludes=("*/__pycache__/*", "*.pyc", "pydsdl/_test.py"),
        )
        for namespace in ("uavcan", "reg"):
            copy(
                self,
                f"{namespace}/*.dsdl",
                os.path.join(submodules, "public_regulated_data_types"),
                os.path.join(self.package_folder, "submodules", "public_regulated_data_types"),
            )

        bin_folder = os.path.join(self.package_folder, "bin")
        nnvg = os.path.join(bin_folder, "nnvg")
        save(
            self,
            nnvg,
            '#!/bin/sh\n'
            'root="$(cd "$(dirname "$0")/.." && pwd)"\n'
            'PYTHONPATH="$root/src:$root/submodules/pydsdl${PYTHONPATH:+:$PYTHONPATH}" '
            'exec "${PYTHON:-python3}" -m nunavut "$@"\n',
        )
        os.chmod(nnvg, os.stat(nnvg).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        save(
            self,
            os.path.join(bin_folder, "nnvg.bat"),
            '@echo off\r\n'
            'setlocal\r\n'
            'set "PYTHONPATH=%~dp0..\\src;%~dp0..\\submodules\\pydsdl;%PYTHONPATH%"\r\n'
            'if not defined PYTHON set "PYTHON=python"\r\n'
            '"%PYTHON%" -m nunavut %*\r\n',
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        # find_package(Nunavut) loads upstream's NunavutConfig.cmake, which provides
        # add_cyphal_library() and NUNAVUT_SUBMODULES_DIR.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = ["."]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        dsdl = os.path.join(self.package_folder, "submodules", "public_regulated_data_types")
        self.conf_info.define_path("user.nunavut:public_regulated_data_types", dsdl)
