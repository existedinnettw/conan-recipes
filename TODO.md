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
