#include <cstdlib>
#include <iostream>

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQuickWindow>

#include <Kirigami/Platform/TabletModeWatcher>
#include <Kirigami/Platform/kirigamiplatform_version.h>

int main(int argc, char **argv) {
    // Render nothing on screen, so the test runs without a display server.
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);

    std::cout << "Kirigami " << KIRIGAMIPLATFORM_VERSION_STRING << "\n";

    // C++ API of KF6::KirigamiPlatform.
    auto *watcher = Kirigami::Platform::TabletModeWatcher::self();
    std::cout << "tablet mode available: " << watcher->isTabletModeAvailable() << "\n";

    // The QML modules, found through QML_IMPORT_PATH from the package's run environment.
    QQmlApplicationEngine engine;
    engine.loadData(R"(
        import QtQuick
        import org.kde.kirigami as Kirigami

        Kirigami.ApplicationWindow {
            visible: false
            pageStack.initialPage: Kirigami.ScrollablePage {
                title: "test_package"
                Kirigami.FormLayout {
                    Kirigami.Heading { text: "Kirigami"; level: 2 }
                }
            }
        }
    )");

    if (engine.rootObjects().isEmpty()) {
        std::cerr << "failed to load a Kirigami.ApplicationWindow\n";
        return EXIT_FAILURE;
    }
    auto *window = qobject_cast<QQuickWindow *>(engine.rootObjects().constFirst());
    std::cout << "loaded " << engine.rootObjects().constFirst()->metaObject()->className()
              << (window ? " (QQuickWindow)" : "") << "\n";
    return window ? EXIT_SUCCESS : EXIT_FAILURE;
}
