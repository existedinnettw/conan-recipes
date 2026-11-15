#include <SensorFusion.h>
#include <cmath>

bool valid(const Quaternion& q) {
    return std::isfinite(q.magnitudeSquared()) && std::fabs(q.magnitudeSquared() - 1.f) < 1e-3f;
}

int main() {
    const xyz_t still{0.f, 0.f, 0.f};
    const xyz_t acc{0.f, 0.f, 1.f};
    const xyz_t mag{1.f, 0.f, 0.f};
    MahonyFilter mahony;
    mahony.setKpKi(1.f, 0.f);
    for (int i = 0; i < 100; ++i) {
        if (!valid(mahony.updateOrientation(still, acc, mag, 0.01f))) return 1;
    }
    // Constant yaw rate with accelerometer only should integrate to one radian.
    mahony.reset();
    for (int i = 0; i < 100; ++i) {
        mahony.updateOrientation(xyz_t{0.f, 0.f, 1.f}, acc, 0.01f);
    }
    const Quaternion yaw = mahony.getOrientation();
    if (!valid(yaw) || std::fabs(yaw.calculateYawRadians() - 1.f) > 0.01f) return 2;
    MahonyFilter interpolated(true, true);
    if (!valid(interpolated.updateOrientation(xyz_t{0.f, 0.f, 0.1f}, acc, 0.01f))) return 3;
    ComplementaryFilter complementary;
    MadgwickFilter madgwick;
    BasicVQF basic(0.01f);
    VQF vqf(0.01f);
    SensorFusionFilterBase* filters[] = {&complementary, &madgwick, &basic, &vqf};
    for (SensorFusionFilterBase* filter : filters) {
        if (!valid(filter->updateOrientation(still, xyz_t{0.01f, 0.02f, 1.f}, 0.01f))) return 4;
    }
    return 0;
}
