# zephyr-sdk

Zephyr SDK (GNU cross toolchains, optional Yocto host tools) as a Conan
**tool requirement**. Completes the "Conan outside" graph together with the
`zephyr` recipe:

```text
firmware
├── tool_requires  zephyr-sdk/1.0.1   toolchains, runs on the build machine
├── tool_requires  zephyr/4.4.0       pinned west workspace (ZEPHYR_BASE)
└── build()        west build [--sysbuild] ...
```

`package_info()` exports `ZEPHYR_SDK_INSTALL_DIR` and
`ZEPHYR_TOOLCHAIN_VARIANT=zephyr` into the build environment, prepends the
selected toolchains' `bin/` to `PATH`, and prepends the package to
`CMAKE_PREFIX_PATH` so this SDK wins over any other same-version SDK visible
to CMake (verified against the nix shell's own SDK). Nothing is registered in the CMake user
package registry (no `setup.sh -c`); Zephyr's `FindZephyr-sdk.cmake` finds the
SDK through the environment variable. Conan's `CMakeToolchain` is never
involved; Zephyr keeps owning the toolchain file.

## Options

| option | default | meaning |
|---|---|---|
| `toolchains` | `arm-zephyr-eabi` | comma-separated GNU targets from `sdk_gnu_toolchains`, or `all` |
| `hosttools` | `False` | install the Yocto host tools (qemu, openocd, dtc, ...). Linux only |

Pass options with `-o:b`/`-o:a` because the package lives in the build context.

## Versions and compatibility

| SDK | Zephyr |
|---|---|
| 1.0.x | >= 4.4 (SDK 1.0 is not backward compatible) |
| 0.17.x | 4.3 (and older 4.x) |

Prebuilt hosts: linux-x86_64, linux-aarch64, macos-aarch64 (0.17.4 also
macos-x86_64). Windows uses 7z bundles and is not handled.

`conandata.yml` is generated from the upstream `sha256.sum` release asset.
