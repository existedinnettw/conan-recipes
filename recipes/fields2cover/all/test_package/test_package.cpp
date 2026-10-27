#include <fields2cover.h>

#include <cmath>
#include <cstdio>

int main() {
  f2c::types::LinearRing boundary;
  boundary.addPoint(0.0, 0.0);
  boundary.addPoint(20.0, 0.0);
  boundary.addPoint(20.0, 10.0);
  boundary.addPoint(0.0, 10.0);
  boundary.addPoint(0.0, 0.0);

  const f2c::types::Cell field(boundary);
  f2c::sg::BruteForce swath_generator;
  const auto swaths = swath_generator.generateSwaths(0.0, 2.0, field);
  if (swaths.size() == 0) {
    std::puts("no swaths generated");
    return 1;
  }

  const f2c::types::Robot robot(2.0, 4.0);
  f2c::pp::DubinsCurves turn;
  const auto path = turn.createTurn(robot, swaths.at(0).endPoint(), 0.0,
                                    swaths.back().startPoint(), 0.0);
  std::printf("Generated %zu swaths and a %.3f m turn\n", swaths.size(), path.length());
  return std::isfinite(path.length()) ? 0 : 1;
}
