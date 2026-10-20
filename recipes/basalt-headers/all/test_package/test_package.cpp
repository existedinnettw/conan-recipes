#include <basalt/calibration/calibration.hpp>
#include <basalt/camera/double_sphere_camera.hpp>
#include <basalt/serialization/headers_serialization.h>
#include <basalt/spline/se3_spline.h>

#include <cereal/archives/json.hpp>

#include <cmath>
#include <iostream>
#include <sstream>

int main()
{
    Eigen::Matrix<double, 6, 1> params;
    params << 300.0, 300.0, 320.0, 240.0, -0.2, 0.6;
    basalt::DoubleSphereCamera<double> camera(params);

    const Eigen::Vector4d point(0.1, -0.2, 1.0, 1.0);
    Eigen::Vector2d proj;
    Eigen::Vector4d unproj;
    const bool ok = camera.project(point, proj) && camera.unproject(proj, unproj);
    const double err = (unproj.head<3>() - point.head<3>().normalized()).norm();

    basalt::Se3Spline<5> spline(int64_t(1e8));
    spline.setKnots(Sophus::SE3d(), 8);
    const Sophus::SE3d pose = spline.pose(int64_t(2e8));

    basalt::Calibration<double> calib;
    std::stringstream ss;
    {
        cereal::JSONOutputArchive archive(ss);
        archive(cereal::make_nvp("value0", calib));
    }

    std::cout << "projected: " << proj.transpose() << ", round-trip error: " << err << std::endl;
    std::cout << "spline translation: " << pose.translation().transpose() << std::endl;
    std::cout << "calibration json bytes: " << ss.str().size() << std::endl;
    return ok && err < 1e-9 && pose.translation().norm() < 1e-12 ? 0 : 1;
}
