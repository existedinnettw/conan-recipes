#include <Inventor/SoDB.h>
#include <Inventor/SoInteraction.h>
#include <Inventor/SoOutput.h>
#include <Inventor/actions/SoGetBoundingBoxAction.h>
#include <Inventor/actions/SoWriteAction.h>
#include <Inventor/nodes/SoCube.h>
#include <Inventor/nodes/SoSeparator.h>
#include <Inventor/nodes/SoTranslation.h>

#include <cmath>
#include <cstdio>

int main()
{
    // No OpenGL context is needed for scene graph traversals that do not render.
    SoDB::init();
    SoInteraction::init();

    SoSeparator * root = new SoSeparator;
    root->ref();
    SoTranslation * translation = new SoTranslation;
    translation->translation.setValue(1.0f, 0.0f, 0.0f);
    root->addChild(translation);
    SoCube * cube = new SoCube;
    cube->width = 2.0f;
    root->addChild(cube);

    SoGetBoundingBoxAction bbox(SbViewportRegion(640, 480));
    bbox.apply(root);
    const SbVec3f center = bbox.getBoundingBox().getCenter();

    SoOutput out;
    SoWriteAction write(&out);
    write.apply(root);

    root->unref();
    std::printf("bounding box center: %g %g %g\n", center[0], center[1], center[2]);
    return std::fabs(center[0] - 1.0f) < 1e-6f ? 0 : 1;
}
