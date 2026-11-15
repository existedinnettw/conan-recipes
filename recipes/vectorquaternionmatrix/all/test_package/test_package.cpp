#include <Matrix2x2.h>
#include <Matrix3x3.h>
#include <FastTrigonometry.h>
#include <cmath>

int main() {
    const Quaternion q = Quaternion::fromEulerAnglesDegrees(0.f, 0.f, 90.f);
    const xyz_t rotated = q.rotate(xyz_t{1.f, 0.f, 0.f});
    const Quaternion normalized = Quaternion(2.f, 0.f, 0.f, 0.f).normalized();
    const Quaternion from_matrix = Matrix3x3::fromEulerAnglesDegrees(0.f, 0.f, 90.f).quaternion();
    return std::fabs(rotated.x) < 1e-4f && std::fabs(rotated.y - 1.f) < 1e-4f &&
           std::fabs(normalized.getW() - 1.f) < 1e-4f &&
           std::fabs(from_matrix.calculateYawDegrees() - 90.f) < 1e-3f ? 0 : 1;
}
