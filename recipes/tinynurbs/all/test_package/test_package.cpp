#include <tinynurbs/tinynurbs.h>

#include <cmath>
#include <iostream>

int main()
{
  tinynurbs::Curve<float> crv;
  crv.control_points = {glm::vec3(-1, 0, 0), glm::vec3(0, 1, 0), glm::vec3(1, 0, 0)};
  crv.knots = {0, 0, 0, 1, 1, 1};
  crv.degree = 2;
  if (!tinynurbs::curveIsValid(crv))
    return 1;

  const glm::vec3 pt = tinynurbs::curvePoint(crv, 0.5f);
  std::cout << "curvePoint(0.5) = " << pt.x << " " << pt.y << " " << pt.z << std::endl;

  crv = tinynurbs::curveKnotInsert(crv, 0.25f);
  const glm::vec3 pt2 = tinynurbs::curvePoint(crv, 0.5f);
  return std::abs(pt.y - 0.5f) < 1e-6f && glm::length(pt - pt2) < 1e-6f ? 0 : 1;
}
