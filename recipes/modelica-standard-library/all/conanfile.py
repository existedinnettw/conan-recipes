import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir


class ModelicaStandardLibraryConan(ConanFile):
    """Modelica Standard Library (MSL), the Modelica libraries almost every model uses.

    The package is data only: the libraries are installed as ``libraries/<Name> <version>``
    and put on ``MODELICAPATH`` (and, for OpenModelica, ``OPENMODELICALIBRARY``) in both
    the build and the run environment.
    """

    name = "modelica-standard-library"
    description = "Modelica Standard Library: Modelica, ModelicaServices, Complex and ModelicaReference"
    license = "BSD-3-Clause"
    url = "https://github.com/modelica/ModelicaStandardLibrary"
    homepage = "https://github.com/modelica/ModelicaStandardLibrary"
    topics = ("modelica", "msl", "simulation", "modeling")
    package_type = "unknown"

    options = {
        # ModelicaServices is the tool specific part of the MSL. "default" is the reference
        # implementation shipped in the release; "openmodelica" applies the changes
        # OpenModelica makes to its own distribution.
        "modelica_services": ["default", "openmodelica"],
    }
    default_options = {
        "modelica_services": "default",
    }

    @property
    def _libraries(self):
        return ("Modelica", "ModelicaServices", "ModelicaReference")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "src"

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def build(self):
        # The sources are copied to the build folder, so option dependent patches do not
        # leak into the shared source folder.
        if self.options.modelica_services == "openmodelica":
            apply_conandata_patches(self)
            # Prebuilt ModelicaExternalC libraries; OpenModelica links its own.
            rmdir(self, os.path.join(self.build_folder, f"Modelica {self.version}", "Resources", "Library"))

    def package(self):
        copy(self, "LICENSE", src=self.build_folder, dst=os.path.join(self.package_folder, "licenses"))
        libraries = os.path.join(self.package_folder, "libraries")
        for lib in self._libraries:
            directory = f"{lib} {self.version}"
            copy(self, "*", src=os.path.join(self.build_folder, directory), dst=os.path.join(libraries, directory))
        for lib in ("Complex", "ObsoleteModelica4"):
            copy(self, f"{lib}.mo", src=self.build_folder, dst=libraries)
            os.replace(os.path.join(libraries, f"{lib}.mo"), os.path.join(libraries, f"{lib} {self.version}.mo"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_find_mode", "none")

        libraries = os.path.join(self.package_folder, "libraries")
        for env in (self.buildenv_info, self.runenv_info):
            # MODELICAPATH is the search path the Modelica specification defines.
            env.append_path("MODELICAPATH", libraries)
            if self.options.modelica_services == "openmodelica":
                # omc ignores MODELICAPATH, and without OPENMODELICALIBRARY only searches
                # ~/.openmodelica/libraries.
                env.append_path("OPENMODELICALIBRARY", libraries)
