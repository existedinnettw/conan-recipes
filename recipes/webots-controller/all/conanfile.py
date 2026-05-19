from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import chdir, copy, get
from conan.tools.scm import Git
from pathlib import Path
import os
import shutil
import subprocess
import platform


def find_webots_install_path() -> str | None:
    """Locate an existing Webots installation directory.

    Windows strategy (in order):
    1. Respect WEBOTS_HOME environment variable if it points to an existing path.
    2. Query uninstall registry keys (both 64-bit and 32-bit views) for InstallLocation:
       HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Webots
    3. Look in common default install directories (Program Files, Program Files (x86)).
    4. Fallback: derive from a discovered `webots-controller.exe` on PATH.

    macOS strategy:
    * If a `webots` or `webots-controller` binary is found inside a Webots.app bundle,
      return the bundle root (…/Webots.app).

    Linux / Other:
    * Attempt to locate `webots-controller` or `webots` via PATH and return its parent directory.

    Returns None if nothing suitable is found.
    """

    system = platform.system()

    # 1. Explicit env var (all platforms)
    env_home = os.getenv("WEBOTS_HOME")
    if env_home and os.path.exists(env_home):
        return env_home

    if system == "Windows":
        # 2. Registry (both views)
        try:  # pragma: no cover (import guarded for non-Windows)
            import winreg  # type: ignore
        except ImportError:  # pragma: no cover
            winreg = None  # type: ignore

        if winreg:
            reg_paths = [
                (
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Webots",
                ),
                # 32-bit view on 64-bit systems
                (
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Webots",
                ),
            ]
            for hive, subkey in reg_paths:
                try:
                    with winreg.OpenKey(hive, subkey) as key:  # type: ignore[attr-defined]
                        install_path, _ = winreg.QueryValueEx(key, "InstallLocation")  # type: ignore[attr-defined]
                        if install_path and os.path.exists(install_path):
                            return install_path
                except FileNotFoundError:
                    pass
                except OSError:
                    pass

        # 3. Common default directories
        program_files = os.environ.get("ProgramFiles", r"C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")
        candidates = [
            os.path.join(program_files, "Webots"),
            os.path.join(program_files_x86, "Webots"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c

        # 4. PATH discovery of controller exe
        exe = shutil.which("webots-controller.exe") or shutil.which("webots.exe")
        if exe:
            parent = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(exe)))
            )  # heuristic
            # Explanation: typical Windows structure:
            # <WEBOTS_HOME>\msys64\mingw64\bin\webots-controller.exe
            # So we ascend four levels to reach WEBOTS_HOME.
            if os.path.exists(parent):
                return parent
        return None

    # Non-Windows
    candidate = shutil.which("webots-controller") or shutil.which("webots")
    if not candidate:
        return None

    # Resolve symlinks to get actual installation root. This matters on Linux
    # distributions where Webots may be installed under /opt/webots but only a
    # symlink placed into /usr/local/bin or similar locations.
    resolved = os.path.realpath(candidate)

    if system == "Darwin":
        token = "Webots.app"
        # If the resolved path sits inside an app bundle, return the bundle root.
        if token in resolved:
            prefix, _sep, _rest = resolved.partition(token)
            return os.path.join(prefix, token)
        # Fallback: just use the directory of the (possibly resolved) binary.
        return os.path.dirname(resolved)

    return os.path.dirname(resolved)


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

    @property
    def _is_system_package(self):
        return str(self.version) == "system"

    @property
    def _system_webots_home(self):
        webots_home = find_webots_install_path()
        if not webots_home:
            raise ConanInvalidConfiguration(
                f"{self.ref} could not locate an installed Webots root. "
                "Set WEBOTS_HOME or install Webots in a standard location discoverable by find_webots_install_path()."
            )
        return os.path.abspath(os.path.expanduser(webots_home))

    def _validate_system_webots_home(self):
        webots_home = self._system_webots_home
        required_paths = [
            os.path.join(webots_home, "include", "controller", "c", "webots", "robot.h"),
            os.path.join(webots_home, "include", "controller", "cpp", "webots", "Robot.hpp"),
            os.path.join(webots_home, "lib", "controller"),
        ]
        missing = [path for path in required_paths if not os.path.exists(path)]
        if missing:
            formatted = ", ".join(f"'{path}'" for path in missing)
            raise ConanInvalidConfiguration(
                f"{self.ref} could not find the expected Webots controller files under WEBOTS_HOME='{webots_home}': {formatted}"
            )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        if self._is_system_package:
            self._validate_system_webots_home()
            return
        if str(self.settings.compiler) == "msvc":
            raise ConanInvalidConfiguration("Webots controller libraries are built with GCC/Clang toolchains, not MSVC")

    def source(self):
        if self._is_system_package:
            return
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

    def requirements(self):
        # [Using a MinGW as tool_requires to build with gcc in Windows](https://docs.conan.io/2/examples/dev_flow/tool_requires/mingw.html#examples-dev-flow-tool-requires-mingw)
        if not self._is_system_package and self.settings.os == "Windows":
            self.tool_requires("msys2/cci.latest")

    def package_id(self):
        if self._is_system_package:
            self.info.clear()

    def build(self):
        if self._is_system_package:
            return
        source_root = os.path.join(self.source_folder, self._source_subfolder)
        if self.settings.os == "Windows":
            # Webots makefiles invoke POSIX tools and shell fragments, so run MSYS make from bash.
            bash_exe = None
            make_exe = None
            for dep in self.dependencies.build.values():
                if not dep.ref or not dep.package_folder:
                    continue
                if dep.ref.name == "msys2":
                    bash_matches = list(Path(dep.package_folder).glob("**/bash.exe"))
                    make_matches = list(Path(dep.package_folder).glob("**/make.exe"))
                    if bash_matches and not bash_exe:
                        bash_exe = str(bash_matches[0])
                    if make_matches and not make_exe:
                        make_exe = str(make_matches[0])
            if not bash_exe or not make_exe:
                raise ConanInvalidConfiguration(
                    "Windows build requires bash.exe and make.exe from tool_requires 'msys2'."
                )
            mingw_dep = next((dep for dep in self.dependencies.build.values() if dep.ref and dep.ref.name == "mingw-builds"), None)
            if mingw_dep is None:
                raise ConanInvalidConfiguration("Windows build requires tool_requires 'mingw-builds'.")
            env = os.environ.copy()
            env["WEBOTS_HOME"] = source_root
            env["PATH"] = os.pathsep.join([
                os.path.join(mingw_dep.package_folder, "bin"),
                str(Path(make_exe).parent),
                env.get("PATH", ""),
            ])
            drive, tail = os.path.splitdrive(make_exe)
            msys_make = f"/{drive[0].lower()}{tail.replace('\\', '/')}"
            for controller_dir in ("c", "cpp"):
                cwd = os.path.join(source_root, "src", "controller", controller_dir)
                subprocess.run([bash_exe, "--noprofile", "--norc", "-c", f'"{msys_make}" clean'], cwd=cwd, env=env, check=True)
                subprocess.run([bash_exe, "--noprofile", "--norc", "-c", f'"{msys_make}" release'], cwd=cwd, env=env, check=True)
        else:
            build_env = Environment()
            build_env.define("WEBOTS_HOME", source_root)
            with build_env.vars(self).apply():
                with chdir(self, os.path.join(source_root, "src", "controller", "c")):
                    self.run("make clean")
                    self.run("make release")
                with chdir(self, os.path.join(source_root, "src", "controller", "cpp")):
                    self.run("make clean")
                    self.run("make release")

        expected_artifacts = {
            "Linux": ["libController.so", "libCppController.so"],
            "Macos": ["libController.dylib", "libCppController.dylib"],
            "Windows": ["Controller.dll", "libController.a", "CppController.dll", "libCppController.a"],
        }
        lib_dir = os.path.join(source_root, "lib", "controller")
        missing = [name for name in expected_artifacts.get(str(self.settings.os), []) if not os.path.exists(os.path.join(lib_dir, name))]
        if missing:
            raise ConanException(
                f"Expected Webots controller artifacts were not produced in '{lib_dir}': {', '.join(missing)}. "
                "On Windows, the upstream Webots controller build may be incompatible with the current MinGW/MSYS toolchain setup."
            )

    def package(self):
        if self._is_system_package:
            return
        source_root = os.path.join(self.source_folder, self._source_subfolder)
        build_root = os.path.join(self.build_folder, self._source_subfolder)
        copy(self, "LICENSE", src=source_root, dst=os.path.join(self.package_folder, "licenses"))

        copy(self, "*.h", src=os.path.join(source_root, "include", "controller", "c"), dst=os.path.join(self.package_folder, "include", "controller", "c"), keep_path=True)
        copy(self, "*.hpp", src=os.path.join(source_root, "include", "controller", "cpp"), dst=os.path.join(self.package_folder, "include", "controller", "cpp"), keep_path=True)

        lib_dst = os.path.join(self.package_folder, "lib")
        bin_dst = os.path.join(self.package_folder, "bin")
        lib_src_candidates = [
            os.path.join(build_root, "lib", "controller"),
            os.path.join(source_root, "lib", "controller"),
        ]
        for lib_src in lib_src_candidates:
            copy(self, "*.so*", src=lib_src, dst=lib_dst, keep_path=False)
            copy(self, "*.dylib*", src=lib_src, dst=lib_dst, keep_path=False)
            copy(self, "*.a", src=lib_src, dst=lib_dst, keep_path=False)
            copy(self, "*.dll", src=lib_src, dst=bin_dst, keep_path=False)
            copy(self, "*.lib", src=lib_src, dst=lib_dst, keep_path=False)

        if self.settings.os == "Linux":
            patchelf = shutil.which("patchelf")
            if patchelf:
                package_lib = os.path.join(self.package_folder, "lib")
                for soname in ("libController.so", "libCppController.so"):
                    lib_path = os.path.join(package_lib, soname)
                    if os.path.exists(lib_path):
                        self.run(f'"{patchelf}" --set-soname "{soname}" "{lib_path}"')

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "webots-controller")
        if self._is_system_package:
            webots_home = self._system_webots_home
            controller_lib_dir = os.path.join(webots_home, "lib", "controller")
            controller_include_dir = os.path.join(webots_home, "include", "controller", "c")
            cpp_controller_include_dir = os.path.join(webots_home, "include", "controller", "cpp")
            extra_libdirs = []
            extra_bindirs = []

            self.cpp_info.bindirs = []
            self.cpp_info.includedirs = []
            self.cpp_info.libdirs = []

            self.buildenv_info.define_path("WEBOTS_HOME", webots_home)
            self.runenv_info.define_path("WEBOTS_HOME", webots_home)

            if self.settings.os == "Windows":
                mingw_bin_dir = os.path.join(webots_home, "msys64", "mingw64", "bin")
                extra_libdirs.append(mingw_bin_dir)
                extra_bindirs.append(mingw_bin_dir)
            elif self.settings.os == "Linux":
                extra_libdirs.append(os.path.join(webots_home, "lib"))

            self.cpp_info.components["controller"].includedirs = [controller_include_dir]
            self.cpp_info.components["controller"].libdirs = [controller_lib_dir, *extra_libdirs]
            if self.settings.os == "Windows":
                self.cpp_info.components["controller"].bindirs = [controller_lib_dir, *extra_bindirs]

            self.cpp_info.components["cpp_controller"].includedirs = [
                cpp_controller_include_dir,
                controller_include_dir,
            ]
            self.cpp_info.components["cpp_controller"].libdirs = [controller_lib_dir, *extra_libdirs]
            if self.settings.os == "Windows":
                self.cpp_info.components["cpp_controller"].bindirs = [controller_lib_dir, *extra_bindirs]
        else:
            self.cpp_info.components["controller"].includedirs = ["include/controller/c"]
            self.cpp_info.components["cpp_controller"].includedirs = ["include/controller/cpp", "include/controller/c"]

        self.cpp_info.components["controller"].libs = ["Controller"]
        self.cpp_info.components["controller"].set_property("cmake_target_name", "Webots::Controller")
        self.cpp_info.components["cpp_controller"].libs = ["CppController"]
        self.cpp_info.components["cpp_controller"].set_property("cmake_target_name", "Webots::CppController")
        self.cpp_info.components["cpp_controller"].requires = ["controller"]

        if self.settings.os == "Linux":
            self.cpp_info.components["controller"].system_libs = ["m", "pthread", "dl", "rt"]
