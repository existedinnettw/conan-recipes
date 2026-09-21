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
  (`tool_requires("zephyr-sdk/1.0.1")`), or from the environment, e.g. the
  `nix develop ~/nix-config#zephyr` shell, which sets `ZEPHYR_SDK_INSTALL_DIR`
  and `ZEPHYR_TOOLCHAIN_VARIANT`. Zephyr never
  receives Conan's `conan_toolchain.cmake`; its own toolchain logic stays in
  charge.
* **west and Zephyr's Python requirements.** Needed both to build this
  package (`west update`) and to consume it (`west build`). The nix shell
  provides them.
* `.git` metadata (unless `keep_git=True`). `west build` does not need it,
  `west update` inside the package will not work.

The SDK major version must match the Zephyr release: Zephyr 4.3 wants SDK
0.17.x, Zephyr 4.4 wants SDK 1.0.x (the current nix shell ships 1.0.1, so
only `zephyr/4.4.0` passes the test package there).

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
