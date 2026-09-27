#include <cstdlib>
#include <iostream>

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQuickItem>
#include <QVariantList>

int main(int argc, char **argv) {
    // Render nothing on screen, so the test runs without a display server.
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);

    // Upstream's BasicSinGraph example. The QML modules are found through
    // QML_IMPORT_PATH from the package's run environment; Helpers.linspace() is
    // implemented in the C++ library behind the QuickGraphLib module.
    QQmlApplicationEngine engine;
    engine.loadData(R"qml(
        import QtQuick
        import QuickGraphLib as QuickGraphLib
        import QuickGraphLib.GraphItems as QGLGraphItems
        import QuickGraphLib.PreFabs as QGLPreFabs

        QGLPreFabs.XYAxes {
            id: axes
            width: 400; height: 300
            viewRect: Qt.rect(-20, -1.1, 760, 2.2)
            xLabel: "Angle (deg)"
            yLabel: "Value"

            QGLGraphItems.Line {
                id: sinLine
                objectName: "sinLine"
                dataTransform: axes.dataTransform
                path: QuickGraphLib.Helpers.linspace(0, 720, 100).map(x => Qt.point(x, Math.sin(x / 180 * Math.PI)))
                strokeColor: "red"
                strokeWidth: 2
            }
        }
    )qml");

    if (engine.rootObjects().isEmpty()) {
        std::cerr << "failed to load the graph\n";
        return EXIT_FAILURE;
    }
    auto *line = engine.rootObjects().constFirst()->findChild<QObject *>("sinLine");
    if (!line) {
        std::cerr << "line missing\n";
        return EXIT_FAILURE;
    }
    const auto points = line->property("path").toList().size();
    std::cout << "loaded " << engine.rootObjects().constFirst()->metaObject()->className()
              << " with a line of " << points << " points\n";
    return points == 100 ? EXIT_SUCCESS : EXIT_FAILURE;
}
