#include <SmApiBrep.h>
#include <SmApiGeneral.h>
#include <SmApiPrimitives.h>
#include <SmApiQueries.h>
#include <SmBrep.h>
#include <SmVector3d.h>

#ifdef TEST_USD
#include <SmApiUsd.h>
#endif

#include <cmath>
#include <cstdio>
#include <iostream>
#include <vector>

int main()
{
    SmApiCreateContext();

    // A 4 x 4 x 1 plate with a through-hole of radius 1.
    SmBrep* plate = nullptr;
    SmBrep* cutter = nullptr;
    SmBrep* result = nullptr;
    if (SmApiCreateBox(SmVector3d(0, 0, 0), 4.0, 4.0, 1.0, plate) != SM_SUCCESS ||
        SmApiCreateCylinder(SmVector3d(2, 2, -1), 1.0, 3.0, cutter) != SM_SUCCESS ||
        SmApiBooleanDifference(plate, cutter, result) != SM_SUCCESS) {
        std::cerr << "boolean failed" << std::endl;
        return 1;
    }

    double volume = 0.0;
    SmApiBrepComputeVolume(result, 1.0e-7, volume);
    const double expected = 16.0 - std::acos(-1.0);
    std::cout << "volume: " << volume << " (expected " << expected << ")" << std::endl;
    if (std::abs(volume - expected) > 1.0e-6 * expected) {
        return 1;
    }

#ifdef TEST_USD
    // Round-trip through a BrepArray prim; needs OMNISOLID_PLUGIN_PATH from the package.
    const char* path = "usd_brep_test_package.usda";
    if (SmApiUsdExportBrep(path, result) != SM_SUCCESS) {
        std::cerr << "USD export failed" << std::endl;
        return 1;
    }
    std::vector<SmBrep*> imported;
    const SmStatus status = SmApiUsdImportBreps(path, imported, FALSE);
    std::remove(path);
    if (status != SM_SUCCESS || imported.size() != 1) {
        std::cerr << "USD import failed" << std::endl;
        return 1;
    }
    double importedVolume = 0.0;
    SmApiBrepComputeVolume(imported[0], 1.0e-7, importedVolume);
    std::cout << "volume after USD round-trip: " << importedVolume << std::endl;
    delete imported[0];
    if (std::abs(importedVolume - expected) > 1.0e-6 * expected) {
        delete result;
        return 1;
    }
#endif

    delete result;
    return 0;
}
