# zephyr

Packages a complete Zephyr **west workspace** (the `zephyr` tree plus every
west-managed module: HALs, CMSIS, MCUboot, ...) pinned to a release tag.

This is the "Conan outside" architecture:

```text
Conan                      package / dependency / environment graph
  ├── zephyr/<version>     (this recipe: pinned west workspace)
  ├── <target libraries>   (ordinary Conan requirements)
  └── build()
        └── west build [--sysbuild] ...   firmware image graph, untouched
```

Conan pins *which* Zephyr platform is available; `west`/sysbuild keep owning
board selection, Kconfig, devicetree, MCUboot, signing and flashing.

## What is *not* in the package

* **Zephyr SDK / toolchain.** Provided by the separate `zephyr-sdk` recipe
  (`tool_requires("zephyr-sdk/1.0.1")`), or from the environment via
  `ZEPHYR_SDK_INSTALL_DIR` and `ZEPHYR_TOOLCHAIN_VARIANT`. Zephyr never
  receives Conan's `conan_toolchain.cmake`; its own toolchain logic stays in
  charge.
* **west and Zephyr's Python requirements.** Needed both to build this
  package (`west update`) and to consume it (`west build`); install them into
  a virtualenv on `PATH` (e.g. `pip install west ninja` plus
  `zephyr/scripts/requirements-base.txt`).
* `.git` metadata (unless `keep_git=True`). `west build` does not need it,
  `west update` inside the package will not work.

The SDK major version must match the Zephyr release: Zephyr 4.3 wants SDK
0.17.x, Zephyr 4.4 wants SDK 1.0.x.

## Options

| option | default | meaning |
|---|---|---|
| `projects` | `""` (all active) | comma-separated west projects to fetch, e.g. `hal_stm32,cmsis_6,mcuboot` |
| `group_filter` | `""` | west `manifest.group-filter`, e.g. `-hal,+hal_stm32` |
| `narrow` | `True` | shallow-fetch modules (`west update --narrow -o=--depth=1`) |
| `keep_git` | `False` | keep `.git` directories in the package |

A full workspace is several GB; restrict `projects`/`group_filter` for one
SoC family.

Zephyr is compiled into the firmware, so consumers declare it with
`requires` (host context) and options are passed with plain `-o`:

```bash
conan create recipes/zephyr/all --version=4.4.0 \
    -o "zephyr/*:projects=hal_stm32,cmsis_6,mcuboot"
```

(The SDK, by contrast, is a `tool_requires`.)

## Consuming

```python
class Firmware(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires("zephyr/4.4.0")            # platform source, compiled into the image

    def build_requirements(self):
        self.tool_requires("zephyr-sdk/1.0.1")   # toolchains, see recipes/zephyr-sdk

    def build(self):
        # ZEPHYR_BASE is exported by the package; west finds the workspace from it.
        self.run(f"west build --sysbuild -b my_board -d {self.build_folder} {self.source_folder}")
```

`package_info()` exports:

* env `ZEPHYR_BASE=<pkg>/zephyr` (build and run env)
* conf `user.zephyr:base`, `user.zephyr:workspace`

It deliberately sets `cmake_find_mode=none`: this package is not a CMake
library, and a CMakeDeps-generated `zephyr-config.cmake` sitting on
`CMAKE_PREFIX_PATH` would shadow Zephyr's own `find_package(Zephyr)`.

## Adding ordinary C++ libraries to the firmware

Zephyr consumes Conan libraries through plain `find_package()`; the working
pattern (see `cpp_garage/zephyr_conan` and `zephyr_conan_sysbuild`) is:

* `generate()` runs only `CMakeDeps` (never `CMakeToolchain`) and prepends
  the generators folder to the **`CMAKE_PREFIX_PATH` environment variable**.
  Environment, not `-D`, so the same setup works under `west build --sysbuild`,
  which does not forward `-DCMAKE_*` to the images it configures.
* CMakeDeps insists on `CMAKE_BUILD_TYPE`, Zephyr leaves it unset and would
  inherit CMake's `-O3 -DNDEBUG` defaults if it were set on the command line.
  Generate a two-file Zephyr module (`zephyr/module.yml` + `CMakeLists.txt`
  that force-sets `CMAKE_BUILD_TYPE`, blanks `CMAKE_<LANG>_FLAGS_<CONFIG>` and
  sets `NO_BUILD_TYPE_WARNING`) and export it with `ZEPHYR_EXTRA_MODULES`.
* The host profile is the board's ABI contract: `os=baremetal`, the SDK's gcc
  via `tools.build:compiler_executables`, Zephyr's exact `-mcpu/-mthumb/
  -specs=picolibc.specs/-fno-exceptions/-fno-rtti` flags in
  `tools.build:cflags/cxxflags`, `*:fPIC=False` (Zephyr links `-fno-pic`),
  `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`, and `zephyr-sdk` in
  `[tool_requires]` so every package in the graph is cross-compiled by it.
* The SDK's `libstdc++` has no gthreads (`std::mutex`, `std::thread`,
  `std::condition_variable` are absent, as Zephyr documents), so libraries
  needing them (e.g. spdlog) only build for `native_sim`; `fmt` builds fine.
