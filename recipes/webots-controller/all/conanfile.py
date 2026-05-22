from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy
from conan.tools.scm import Git
from conan.tools.microsoft import is_msvc
import os


class WebotsControllerConan(ConanFile):
    name = "webots-controller"
    description = "Webots C/C++ robot controller libraries (Controller and CppController)"
    license = "Apache-2.0"
    url = "https://github.com/cyberbotics/webots"
    homepage = "https://cyberbotics.com"
    topics = ("robotics", "simulation", "webots", "controller")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "no_plugins": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "no_plugins": True,
    }

    exports_sources = (
        "CMakeLists.txt",
        "src/*",
        "patches/*.patch",
        "test_package/conanfile.py",
        "test_package/CMakeLists.txt",
        "test_package/test_package.cpp",
        "test_package/test_package.c",
    )

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("no_plugins", True):
            return
        if self.settings.os == "Windows" and is_msvc(self):
            raise ValueError("Official Windows Webots is built with MinGW GCC, not MSVC.")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        if "git_url" in source_data:
            git = Git(self)
            clone_args = ["--depth", "1"]
            if "ref" in source_data:
                clone_args.extend(["--branch", source_data["ref"]])
            git.clone(url=source_data["git_url"], target=self._source_subfolder, args=clone_args)
            if "ref" in source_data:
                git.run(f"-C {self._source_subfolder} checkout {source_data['ref']}")
            git.run("-C {} submodule update --init --recursive --depth 1".format(self._source_subfolder))
            return
        raise ValueError("conandata.yml sources entry must provide git_url/ref for this recipe")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["WEBOTS_CONTROLLER_NO_PLUGINS"] = bool(self.options.no_plugins)
        webots_repo_source_dir = os.path.join(self.source_folder, self._source_subfolder).replace("\\", "/")
        tc.variables["WEBOTS_REPO_SOURCE_DIR"] = webots_repo_source_dir

        libcontroller_version = str(self.version)
        if libcontroller_version.startswith("r"):
            libcontroller_version = f"R{libcontroller_version[1:]}"
        tc.variables["LIBCONTROLLER_VERSION"] = libcontroller_version
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=os.path.join(self.source_folder, self._source_subfolder), dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "webots-controller")

        controller = self.cpp_info.components["Controller"]
        controller.libs = ["webots_controller"]
        controller.includedirs = ["include", "include/controller/c"]
        controller.set_property("cmake_target_name", "webots-controller::Controller")

        cpp_controller = self.cpp_info.components["CppController"]
        cpp_controller.libs = ["webots_cpp_controller"]
        cpp_controller.includedirs = ["include", "include/controller/cpp", "include/controller/c"]
        cpp_controller.requires = ["Controller"]
        cpp_controller.set_property("cmake_target_name", "webots-controller::CppController")

        if self.settings.os == "Linux":
            controller.system_libs = ["m", "pthread", "rt"]
            if not bool(self.options.no_plugins):
                controller.system_libs.append("dl")
