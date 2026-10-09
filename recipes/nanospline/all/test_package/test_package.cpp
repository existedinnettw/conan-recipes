#include <nanospline/BSpline.h>
#include <nanospline/Bezier.h>

#include <cmath>
#include <iostream>

int main()
{
  Eigen::Matrix<double, 4, 2> ctrl_pts;
  ctrl_pts << 0.0, 0.0, 1.0, 1.0, 2.0, 1.0, 3.0, 0.0;

  nanospline::Bezier<double, 2, 3> bezier;
  bezier.set_control_points(ctrl_pts);
  const auto mid = bezier.evaluate(0.5);
  std::cout << "Bezier(0.5) = " << mid.transpose() << std::endl;

#ifdef NANOSPLINE_SYMPY
  // A convex arc has no inflection point.
  if (!bezier.compute_inflections(0.0, 1.0).empty())
    return 1;
#endif

  Eigen::Matrix<double, 8, 1> knots;
  knots << 0, 0, 0, 0, 1, 1, 1, 1;
  nanospline::BSpline<double, 2, 3> bspline;
  bspline.set_control_points(ctrl_pts);
  bspline.set_knots(knots);
  const auto diff = (bspline.evaluate(0.5) - mid).norm();

  return std::abs(mid(0) - 1.5) < 1e-12 && std::abs(mid(1) - 0.75) < 1e-12 && diff < 1e-12 ? 0 : 1;
}
