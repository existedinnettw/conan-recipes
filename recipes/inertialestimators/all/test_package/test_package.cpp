#include <InertialEstimator.h>
#include <cmath>

int main() {
    AHRS_Attitude_SO3 mahony(0.01f);
    for (int i = 0; i < 100; ++i) {
        mahony.compute(0.f, 0.f, 0.f, 0.f, 0.f, -9.81f, 1.f, 0.f, 0.f);
    }
    const float norm = mahony.q0 * mahony.q0 + mahony.q1 * mahony.q1 +
                       mahony.q2 * mahony.q2 + mahony.q3 * mahony.q3;
    if (!std::isfinite(norm) || std::fabs(norm - 1.f) > 1e-4f) return 1;
    IMU_Madgwick madgwick;
    madgwick.compute(0.01f, 0.02f, 0.03f, 0.1f, 0.2f, -9.81f, 0.01f);
    // Instantiate each EKF too: the umbrella header needs transitive MatLib headers,
    // and shared consumers must be able to resolve all estimator constructors.
    IMU_EKF_AV imu(9.81f, 0.01f);
    AHRS_EKF_AV ahrs(9.81f, 0.01f);
    AHRS_Attitude_EKF attitude(9.81f, 0.01f);
    AHRS_Madgwick magnetic;
    return std::isfinite(madgwick.q1) ? 0 : 1;
}
