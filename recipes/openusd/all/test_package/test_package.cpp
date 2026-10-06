#include <iostream>
#include <string>

#include <pxr/base/gf/vec3d.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdGeom/xform.h>

int main() {
  pxr::UsdStageRefPtr stage = pxr::UsdStage::CreateInMemory();
  pxr::UsdGeomXform world = pxr::UsdGeomXform::Define(stage, pxr::SdfPath("/World"));
  world.AddTranslateOp().Set(pxr::GfVec3d(1.0, 2.0, 3.0));

  std::string layer;
  if (!stage->GetRootLayer()->ExportToString(&layer) ||
      layer.find("def Xform \"World\"") == std::string::npos) {
    return 1;
  }

  std::cout << layer;
  return 0;
}
