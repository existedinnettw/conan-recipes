#include <rsmotion/rsmotion.h>

#include <cmath>
#include <cstdio>

int main() {
  using namespace rsmotion;
  using namespace rsmotion::math;

  const CarState start{{Vec3f{0.0f, 0.0f, 0.0f}, Quatf{Vec3f{0.0f, 1.0f, 0.0f}, Anglef::Degrees(0.0f)}}, 1.0f};
  const PointState finish{Vec3f{3.0f, 0.0f, 2.0f}, Quatf{Vec3f{0.0f, 1.0f, 0.0f}, Anglef::Degrees(65.0f)}};
  const auto path = SearchShortestPath(start, finish);
  const auto end = TraversePathNormalized(1.0f, path, start);

  const float error = std::abs(end.Rear.Pos[0] - finish.Pos[0]) +
                      std::abs(end.Rear.Pos[2] - finish.Pos[2]);
  std::printf("Reeds-Shepp path has %zu segments (position error %.6f)\n", path.Segments.size(), error);
  return error < 1.0e-3f ? 0 : 1;
}
