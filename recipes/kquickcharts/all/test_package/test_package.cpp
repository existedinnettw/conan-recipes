#include <cstdlib>
#include <iostream>

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlListReference>
#include <QQuickItem>

int main(int argc, char **argv) {
    // Render nothing on screen, so the test runs without a display server.
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);

    // The QML modules, found through QML_IMPORT_PATH from the package's run environment.
    QQmlApplicationEngine engine;
    engine.loadData(R"(
        import QtQuick
        import org.kde.quickcharts as Charts
        import org.kde.quickcharts.controls as ChartsControls

        Item {
            width: 400; height: 300

            Charts.LineChart {
                id: chart
                objectName: "chart"
                anchors.fill: parent
                colorSource: Charts.ArraySource { array: ["red", "green"] }
                nameSource: Charts.ArraySource { array: ["first", "second"] }
                valueSources: [
                    Charts.ArraySource { array: [1, 2, 3, 2, 1] },
                    Charts.ArraySource { array: [3, 1, 2, 1, 3] }
                ]
            }
            ChartsControls.Legend {
                objectName: "legend"
                chart: chart
            }
        }
    )");

    if (engine.rootObjects().isEmpty()) {
        std::cerr << "failed to load the charts\n";
        return EXIT_FAILURE;
    }
    QObject *root = engine.rootObjects().constFirst();
    auto *chart = root->findChild<QQuickItem *>("chart");
    auto *legend = root->findChild<QQuickItem *>("legend");
    if (!chart || !legend) {
        std::cerr << "chart or legend missing\n";
        return EXIT_FAILURE;
    }
    const QQmlListReference sources(chart, "valueSources");
    std::cout << "loaded " << chart->metaObject()->className() << " with " << sources.count()
              << " value sources, and " << legend->metaObject()->className() << "\n";
    return sources.count() == 2 ? EXIT_SUCCESS : EXIT_FAILURE;
}
