import os
import re
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import copy, get, save


def prepare(conanfile, output=None, defconfig=None, make_modules=None, url=None):
    if conanfile.settings.os != "Linux":
        raise ConanInvalidConfiguration("linux-kbuild-tree requires a Linux target")

    pyreq = conanfile.python_requires["linux-kbuild-tree"]
    version = str(pyreq.ref.version)
    arch = kernel_arch(conanfile)
    cross_compile = _cross_compile(conanfile)
    if cross_compile is None:
        raise ConanInvalidConfiguration(
            "Cross-building a kernel tree requires "
            "tools.build:compiler_executables with a GCC-like C compiler"
        )

    if defconfig is None:
        defconfig = conanfile.conf.get("user.linux-kbuild-tree:defconfig", default="defconfig")
    if make_modules is None:
        make_modules = conanfile.conf.get(
            "user.linux-kbuild-tree:make_modules",
            default=False,
        )
    make_modules = _as_bool(make_modules)
    if url is None:
        url = conanfile.conf.get("user.linux-kbuild-tree:url", default=None)

    linux = output or os.path.join(conanfile.build_folder, "linux-kbuild-tree")
    source_url, sha256 = _linux_source(pyreq.path, version, url=url)

    if not os.path.exists(os.path.join(linux, "Makefile")):
        get(conanfile, source_url, sha256=sha256, destination=linux, strip_root=True)

    jobs = conanfile.conf.get("tools.build:jobs", default=None)
    make_jobs = f" -j{jobs}" if jobs else ""
    make_base = (
        f"make --no-print-directory -C {shlex.quote(linux)}{make_jobs} "
        f"ARCH={shlex.quote(str(arch))} "
        f"CROSS_COMPILE={shlex.quote(str(cross_compile or ''))} "
        f"{_host_warning_flags_args(version)}"
    )

    _install_config(conanfile, pyreq.path, linux, make_base, defconfig)
    conanfile.run(f"{make_base} olddefconfig prepare modules_prepare")

    if make_modules:
        # Required when CONFIG_MODVERSIONS=y and the target kernel exports
        # symbols that are not available from a vendor-provided Module.symvers.
        conanfile.run(f"{make_base} modules")

    kernelrelease = _capture(f"{make_base} kernelrelease")
    compiler = _capture(f"{_cross_gcc(cross_compile)} --version").splitlines()[0]
    info_path = os.path.join(linux, "kbuild-tree-info.txt")

    save(
        conanfile,
        info_path,
        "\n".join(
            [
                f"url={source_url}",
                f"ref={_linux_ref_from_version(version)}",
                f"sha256={sha256 or ''}",
                f"kernelrelease={kernelrelease}",
                f"arch={arch}",
                f"cross_compile={cross_compile or ''}",
                f"compiler={compiler}",
                f"make_modules={make_modules}",
                "",
            ]
        ),
    )

    return {
        "path": linux,
        "info_path": info_path,
        "kernelrelease": kernelrelease,
        "arch": arch,
        "cross_compile": cross_compile or "",
    }


def kernel_arch(conanfile):
    arch = str(conanfile.settings.arch)
    arch_map = {
        "x86": "x86",
        "x86_64": "x86",
        "armv5el": "arm",
        "armv5hf": "arm",
        "armv6": "arm",
        "armv7": "arm",
        "armv7hf": "arm",
        "armv8": "arm64",
        "armv8_32": "arm",
        "armv8.3": "arm64",
        "armv8.5": "arm64",
        "armv8.6": "arm64",
        "armv8.7": "arm64",
        "armv8.8": "arm64",
        "armv8.9": "arm64",
        "ppc32": "powerpc",
        "ppc64": "powerpc",
        "ppc64le": "powerpc",
        "riscv32": "riscv",
        "riscv64": "riscv",
        "s390": "s390",
        "s390x": "s390",
        "sparc": "sparc",
        "sparcv9": "sparc",
        "mips": "mips",
        "mips64": "mips",
    }
    if arch not in arch_map:
        raise ConanInvalidConfiguration(
            f"Cannot derive Linux ARCH from settings.arch={arch!r}; "
            "add this Conan architecture to the recipe arch map"
        )
    return arch_map[arch]


def _linux_ref_from_version(version):
    # Upstream Linux tags base releases as v6.8, while the kernel release
    # and Conan package version are commonly represented as 6.8.0.
    version_parts = str(version).split(".")
    if len(version_parts) == 3 and version_parts[2] == "0":
        return f"v{version_parts[0]}.{version_parts[1]}"
    return f"v{version}"


def _linux_archive_version(version):
    version_parts = str(version).split(".")
    if len(version_parts) == 3 and version_parts[2] == "0":
        return f"{version_parts[0]}.{version_parts[1]}"
    return str(version)


def _linux_source(recipe_path, version, url=None):
    source = _conandata_sources(recipe_path).get(str(version), {})
    source_url = url or source.get("url") or _kernel_cdn_url(version)
    return source_url, source.get("sha256")


def _kernel_cdn_url(version):
    archive_version = _linux_archive_version(version)
    major = archive_version.split(".", 1)[0]
    return (
        f"https://cdn.kernel.org/pub/linux/kernel/v{major}.x/"
        f"linux-{archive_version}.tar.gz"
    )


def _conandata_sources(recipe_path):
    path = os.path.join(recipe_path, "conandata.yml")
    if not os.path.isfile(path):
        return {}

    sources = {}
    current = None
    in_sources = False
    with open(path, encoding="utf-8") as conandata:
        for raw_line in conandata:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped == "sources:":
                in_sources = True
                continue
            if not in_sources:
                continue
            if not line.startswith("  "):
                break
            version_match = re.match(r'^\s{2}"?([^":]+)"?:\s*$', line)
            if version_match:
                current = version_match.group(1)
                sources[current] = {}
                continue
            field_match = re.match(r'^\s{4}([A-Za-z0-9_-]+):\s*"?([^"]*)"?\s*$', line)
            if current and field_match:
                key, value = field_match.groups()
                sources[current][key] = value
    return sources


def _host_warning_flags_args(version):
    hostcflags = []

    if _version_lt(version, "5.16.0") and _host_compiler_accepts("-Wno-error=use-after-free"):
        # Older objtool builds use -Werror and trip GCC 14's realloc(ptr)
        # use-after-free diagnostic in tools/lib/subcmd/subcmd-util.h.
        hostcflags.append("-Wno-error=use-after-free")

    if not hostcflags:
        return ""

    flags = shlex.quote(" ".join(hostcflags))
    return f"HOSTCFLAGS={flags} EXTRA_CFLAGS={flags}"


def _as_bool(value):
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


def _host_compiler_accepts(flag):
    try:
        subprocess.run(
            [
                "gcc",
                flag,
                "-x",
                "c",
                "-c",
                "-o",
                os.devnull,
                "-",
            ],
            input="int main(void) { return 0; }\n",
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def _version_lt(version, other):
    return _version_tuple(str(version)) < _version_tuple(other)


def _version_tuple(version):
    return tuple(int(part) for part in version.split("."))


def _cross_compile(conanfile):
    if not cross_building(conanfile):
        return ""

    c_compiler = _compiler_executable(conanfile, "c")
    if not c_compiler:
        return None

    return _cross_compile_from_executable(c_compiler)


def _cross_compile_from_executable(c_compiler):
    executable = os.path.basename(c_compiler)
    match = re.match(r"^(.+?)(?:gcc|cc)(?:-\d+(?:\.\d+)*)?$", executable)
    if not match:
        return None
    return match.group(1)


def _cross_gcc(cross_compile):
    return shlex.quote(f"{cross_compile or ''}gcc")


def _compiler_executable(conanfile, language):
    executables = conanfile.conf.get("tools.build:compiler_executables", default={})
    if not executables:
        return None
    if hasattr(executables, "get"):
        return executables.get(language)
    return None


def _install_config(conanfile, recipe_path, linux, make_base, defconfig):
    defconfig = "" if defconfig is None else str(defconfig)
    if not defconfig:
        if not os.path.exists(os.path.join(linux, ".config")):
            raise ConanInvalidConfiguration(
                "Missing kernel config: pass defconfig or provide a source tree with .config"
            )
        return

    exported_config = os.path.join(recipe_path, "configs", defconfig)
    if os.path.isfile(exported_config):
        copy(
            conanfile,
            defconfig,
            src=os.path.dirname(exported_config),
            dst=linux,
            keep_path=False,
        )
        os.replace(os.path.join(linux, defconfig), os.path.join(linux, ".config"))
        return

    conanfile.run(f"{make_base} {shlex.quote(defconfig)}")


def _capture(command):
    output = subprocess.check_output(
        command,
        shell=True,
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()
    if not output:
        raise ConanInvalidConfiguration(f"Command produced no output: {command}")
    return output


class LinuxKbuildTreeConan(ConanFile):
    name = "linux-kbuild-tree"
    package_type = "python-require"
    upload_policy = "skip"

    exports = "configs/*"
