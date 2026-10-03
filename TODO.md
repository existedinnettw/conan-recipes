# TODO

## KDE Frameworks for cross-platform Qt Quick apps

Goal: reuse KDE's QtQuick components in our own Qt applications that ship on
Windows, macOS and Linux, not only on KDE-based distributions. KDE publishes no
Conan recipes or remote (its own cross-platform packaging is KDE Craft), so every
framework needs a recipe here.

Done: `extra-cmake-modules`, `kirigami`, `kquickcharts` (plus the non-KDE
`quickgraphlib`).

Platforms are from each framework's `metainfo.yaml` at v6.30.0; tier is KDE's
dependency tier (tier 1 needs only Qt).

### kirigami-addons (1.14.2)

Needs `Kirigami I18n Config CoreAddons GuiAddons ColorScheme` everywhere,
`Crash IconThemes` except on iOS, and `GlobalAccel` only on Linux/FreeBSD. Its
`metainfo.yaml` is a stale KF5-era file; the CMake has explicit Windows, macOS,
Android and iOS branches.

Build order, bottom up:

| Recipe | Tier | Platforms | Needs besides Qt and ECM | Notes |
|---|---|---|---|---|
| `kconfig` | 1 | Linux, FreeBSD, Windows, macOS, Android | Qt Xml, Gui, Qml, DBus | |
| `kcoreaddons` | 1 | + iOS | libmount (Linux), udev/inotify optional | turn off the Python (PySide6) bindings |
| `ki18n` | 1 | Linux, FreeBSD, Windows, macOS, Android | gettext/libintl, Python 3 at build time, iso-codes optional | translations of every other framework go through it |
| `kguiaddons` | 1 | Linux, FreeBSD, Windows, macOS, Android | X11/xcb, Wayland client + wayland-protocols + plasma-wayland-protocols on Linux | Wayland needs Qt with `qtwayland` (see below) |
| `kcolorscheme` | 2 | Linux, FreeBSD, Windows, macOS, Android | KConfig, KGuiAddons, KI18n | |
| `kcrash` | 2 | Linux, FreeBSD, macOS, Windows, Android | KCoreAddons, X11 on Linux | |
| `kglobalaccel` | 1 | Linux, FreeBSD only | Qt DBus, Widgets | only needed on Linux/FreeBSD |
| `karchive` | 1 | Linux, FreeBSD, Windows, macOS, Android | zlib; bzip2, xz, zstd, openssl optional | all on Conan Center |
| `kwidgetsaddons` | 1 | Linux, FreeBSD, Windows, macOS, Android | Qt Widgets | |
| `breeze-icons` | 1 | Linux, FreeBSD, Windows, macOS | none (data) | large; `WITH_ICONS_LIBRARY` (default on) builds `KF6BreezeIcons`, a library with the icons compiled in, so apps off Linux have icons without an installed theme |
| `kiconthemes` | 3 | Linux, FreeBSD, Windows, macOS, Android | KArchive, KI18n, KWidgetsAddons, KColorScheme, breeze-icons (`USE_BreezeIcons`, off on Android) | |
| `kirigami-addons` | – | see above | all of the above | |

### KSvg (6.30.0)

Tier 3, Linux, FreeBSD, Windows, macOS, Android. Needs `KArchive KConfig
KColorScheme KCoreAddons KGuiAddons KirigamiPlatform`, all covered by the
kirigami-addons chain above.

### KIO (6.30.0)

Tier 3, Linux, FreeBSD, Windows, macOS, Android, but heavy: besides the chain above
it needs `KBookmarks KCompletion KDBusAddons KItemViews KJobWidgets KService Solid
KWindowSystem`, `KDED` for its daemon, and optionally `KDocTools`. It runs
file operations in separate worker processes (`kioworker`, `kiod`), which the package
has to ship and the app has to find at runtime. Decide what we actually need from
it before starting; Qt's own file dialogs and QNetworkAccessManager may be enough.

### Others worth a recipe once the base exists

- `knotifications` (tier 2, Linux, FreeBSD, Windows, macOS, Android): KConfig.
- `kpackage` (tier 2, Linux, FreeBSD, Windows, macOS): KArchive, KCoreAddons, KI18n.
- `kwindowsystem` (tier 1, Linux, FreeBSD, macOS, Windows, Android): X11/xcb and
  Wayland on Linux.

### Out of scope: libplasma (formerly plasma-framework)

The library Plasma's desktop shell and plasmoids are built on (6.7.x). It is not
meant for standalone apps, only targets Plasma on Linux/FreeBSD, and needs most of
the above plus KIO, KSvg, KNotifications, KPackage, PlasmaActivities and Qt
Wayland.

### Decisions before the next recipes

- **One Qt option set for all KDE recipes.** Every recipe here sets the same
  `qt/*` default options, so one Qt binary serves all of them, and an app using
  several of them gets no conflicting Qt options. KGuiAddons and KWindowSystem want
  Qt's Wayland client, so the shared set should gain `qtwayland=True` and
  `with_egl=True` (also gives native Wayland windows on Linux). That changes the
  Qt package id: one more multi-hour Qt build, and the existing recipes change with
  it.
- **Qt must be built as gnu++** (`-s qt/*:compiler.cppstd=gnu23`): Qt 6.11 refuses
  to build its library in strict ISO mode with libstdc++. The recipes' `ci-args`
  do this for CI.
- **Windows and macOS CI.** CI only runs on Linux; the cross-platform goal needs
  at least one Windows and one macOS job (Qt from source there too).

## LVGL on Zephyr

The `lvgl` recipe covers hosted targets (SDL2, Linux fbdev/DRM/evdev, Wayland).
For Zephyr, use Zephyr's own LVGL and do not add a recipe. Facts from Zephyr 4.4
that decide it:

- The glue lives in the zephyr repo (`zephyr/modules/lvgl`), not in the LVGL
  module. The module (`modules/lib/gui/lvgl`, Zephyr's fork, LVGL 9.5.0 at 4.4)
  is bare sources: its `module.yml` sets `cmake-ext: True`, and Zephyr's
  `CMakeLists.txt` lists ~380 LVGL source files by path.
- So Zephyr's glue fits exactly one LVGL version, and the version comes with
  Zephyr. LVGL 9.6 already moved the public headers to `include/lvgl/`, which
  Zephyr 4.4's glue (`${LVGL_DIR}/src/`) does not know about.
- Configuration is Kconfig: Zephyr declares the `CONFIG_LV_*` symbols itself and
  ships an `lv_conf.h` that wires LVGL to Zephyr: `k_heap` allocator, `__ASSERT`,
  an OSAL on `k_thread`/`k_mutex`, and display/input devices from devicetree.

What that means for the three options considered before:

- **Configure through west**: the recommended one, and it already works:
  add `lvgl` to `zephyr/*:projects` and set `CONFIG_LVGL=y` plus `CONFIG_LV_*`
  in `prj.conf`. Nothing to build or package.
- **Wrap the west module in Conan**: drop it. The module has no build logic of
  its own, so a package of it only re-ships what the `zephyr` recipe's workspace
  already fetches, and swapping in another LVGL version breaks Zephyr's file
  list.
- **Conan module without west** (build this recipe with the Zephyr SDK): drop it
  for Zephyr. A prebuilt LVGL loses Kconfig and the glue above, which would have to
  be rewritten. It needs one binary per SoC and per configuration (color depth,
  fonts, memory), and hits the `CMAKE_BUILD_TYPE` and flag mismatches from the
  "Conan outside" experiment. Building this recipe for an MCU is worth revisiting
  only for a non-Zephyr target (bare metal, FreeRTOS).

The real need is sharing UI code between a PC build and the Zephyr target:

- **Simulate on `native_sim`, not with this recipe.** Zephyr has an SDL display
  driver for `native_sim` (`zephyr,sdl-dc`, `CONFIG_SDL_DISPLAY`, host
  `libsdl2-dev`). A `native_sim/native/64` build runs the same LVGL, Kconfig
  config and glue as the board, so nothing can drift. Use the `lvgl` recipe for
  products that are themselves Linux or desktop apps.
- **If the UI must also build against this recipe** (say a Linux HMI and a Zephyr
  panel sharing screens): keep it a source library that uses only the public
  API, compiled by each build, never prebuilt. Pin the recipe to the LVGL version
  of the Zephyr manifest (add `9.5.0` to `conandata.yml`). Mirror the few
  `CONFIG_LV_*` settings that matter through `extra_defines`: LVGL reads the same
  names (`LV_*` here, `CONFIG_LV_*` in Kconfig). Zephyr apps write
  `#include <lvgl.h>`, while this recipe gives `<lvgl/lvgl.h>`. Adding
  `include/lvgl` to the recipe's include dirs would make both spellings work.

## HierBEM (deferred)

[HierBEM](https://github.com/jihuan-tian/hierbem) (H-matrix Galerkin BEM, v1.0.0,
LGPL-3.0) was asked for together with `hpddm`, `bemuse`, `nemoh` and `pi-bem`, but
cannot be packaged with what this repo and its CI have:

- **CUDA is mandatory.** The project declares `LANGUAGES CUDA CXX`, and
  `libhierbem` itself has `.cu` sources (ACA+, Sauter quadrature, the Laplace BEM).
  Neither this machine nor the CI runners have a CUDA toolkit; without a GPU, a
  test package could only link, not run kernels.
- **A forked deal.II.** It needs the author's
  [deal.II 9.4.1-cuda12 fork](https://github.com/jihuan-tian/dealii), built with
  `DEAL_II_WITH_CUDA` (upstream dropped that in 9.5 for Kokkos) plus MPI, complex
  values, LAPACK, muParser, HDF5, TBB, OpenCASCADE and Gmsh. The `dealii` recipe
  here is 9.8.0 with none of the last six.
- **A forked Gmsh.** The [author's Gmsh 4.14 fork](https://github.com/jihuan-tian/gmsh)
  (branch `1-expose-internal-functions-of-the-class-occ_internals`), built with
  OpenCASCADE. Conan Center has no Gmsh at all.
- Also reflect-cpp, fmt, cpptrace and toml++ (all on Conan Center), and no
  `install()` rules: upstream only builds `libhierbem.so` and its tests in the
  build tree.

Needed before starting: a CUDA toolkit on CI (several GB of apt packages, or a
CUDA container) and on the dev host, then recipes for the two forks (deal.II as
its own recipe or a `9.4.1-cuda12` version of `dealii`), then `hierbem` with its
own install rules.
