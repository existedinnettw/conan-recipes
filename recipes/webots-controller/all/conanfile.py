from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import chdir, copy, get
from conan.tools.scm import Git
import os


class WebotsControllerConan(ConanFile):
    name = "webots-controller"
    description = "Webots C/C++ robot controller libraries (Controller and CppController)"
    license = "Apache-2.0"
    url = "https://github.com/cyberbotics/webots"
    homepage = "https://cyberbotics.com"
    topics = ("robotics", "simulation", "webots", "controller")
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    exports_sources = (
        "test_package/conanfile.py",
        "test_package/CMakeLists.txt",
        "test_package/test_package.cpp",
    )

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.compiler) == "msvc":
            raise ConanInvalidConfiguration("Webots controller libraries are built with GCC/Clang toolchains, not MSVC")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        if "git_url" in source_data:
            git = Git(self)
            clone_args = [
                "--depth",
                "1",
            ]
            if "ref" in source_data:
                clone_args.extend(["--branch", source_data["ref"]])
            git.clone(url=source_data["git_url"], target=self._source_subfolder, args=clone_args)
            with chdir(self, os.path.join(self.source_folder, self._source_subfolder)):
                if "ref" in source_data:
                    git.checkout(source_data["ref"])
                git.run("submodule update --init --recursive --depth 1")
            return
        get(self, **source_data, strip_root=True, destination=self._source_subfolder)

    def build(self):
        build_env = Environment()
        source_root = os.path.join(self.source_folder, self._source_subfolder)
        build_env.define("WEBOTS_HOME", source_root)
        with build_env.vars(self).apply():
            with chdir(self, os.path.join(source_root, "src", "controller", "c")):
                self.run("make release")
            with chdir(self, os.path.join(source_root, "src", "controller", "cpp")):
                self.run("make release")

    def package(self):
        source_root = os.path.join(self.source_folder, self._source_subfolder)
        copy(self, "LICENSE", src=source_root, dst=os.path.join(self.package_folder, "licenses"))

        copy(self, "*.h", src=os.path.join(source_root, "include", "controller", "c"), dst=os.path.join(self.package_folder, "include", "controller", "c"), keep_path=True)
        copy(self, "*.hpp", src=os.path.join(source_root, "include", "controller", "cpp"), dst=os.path.join(self.package_folder, "include", "controller", "cpp"), keep_path=True)

        lib_src = os.path.join(source_root, "lib", "controller")
        copy(self, "*.so*", src=lib_src, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.dylib*", src=lib_src, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.dll", src=lib_src, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.lib", src=lib_src, dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "webots-controller")

        self.cpp_info.components["controller"].libs = ["Controller"]
        self.cpp_info.components["controller"].set_property("cmake_target_name", "Webots::Controller")
        self.cpp_info.components["controller"].includedirs = ["include/controller/c"]

        self.cpp_info.components["cpp_controller"].libs = ["CppController"]
        self.cpp_info.components["cpp_controller"].set_property("cmake_target_name", "Webots::CppController")
        self.cpp_info.components["cpp_controller"].requires = ["controller"]
        self.cpp_info.components["cpp_controller"].includedirs = ["include/controller/cpp", "include/controller/c"]

        if self.settings.os == "Linux":
            self.cpp_info.components["controller"].system_libs = ["m", "pthread", "dl", "rt"]
