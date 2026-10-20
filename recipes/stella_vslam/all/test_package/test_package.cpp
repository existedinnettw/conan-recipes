#include <stella_vslam/camera/camera_factory.h>
#include <stella_vslam/config.h>

#include <fbow/vocabulary.h>
#include <nlohmann/json.hpp>

#include <cmath>
#include <iostream>
#include <memory>

static const char* kConfig = R"(
Camera:
  name: "test perspective"
  setup: "monocular"
  model: "perspective"
  fx: 500.0
  fy: 500.0
  cx: 320.0
  cy: 240.0
  k1: 0.0
  k2: 0.0
  p1: 0.0
  p2: 0.0
  k3: 0.0
  fps: 30.0
  cols: 640
  rows: 480
  color_order: "Gray"
)";

int main()
{
    auto cfg = std::make_shared<stella_vslam::config>(YAML::Load(kConfig), "inline");
    std::unique_ptr<stella_vslam::camera::base> camera(
        stella_vslam::camera::camera_factory::create(cfg->yaml_node_["Camera"]));

    stella_vslam::Vec2_t reproj;
    float x_right = 0.0f;
    const bool visible = camera->reproject_to_image(
        stella_vslam::Mat33_t::Identity(), stella_vslam::Vec3_t::Zero(),
        stella_vslam::Vec3_t(0.2, -0.1, 1.0), reproj, x_right);
    std::cout << camera->to_json().dump() << std::endl;
    std::cout << "reprojected: " << reproj.transpose() << std::endl;

    fbow::Vocabulary vocabulary;
    std::cout << "empty vocabulary valid: " << vocabulary.isValid() << std::endl;

    const bool ok = visible && std::abs(reproj.x() - 420.0) < 1e-6 && std::abs(reproj.y() - 190.0) < 1e-6;
    return ok ? 0 : 1;
}
