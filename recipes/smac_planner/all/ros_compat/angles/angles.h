#ifndef SMAC_PLANNER_ROS_COMPAT_ANGLES_ANGLES_H
#define SMAC_PLANNER_ROS_COMPAT_ANGLES_ANGLES_H

#include <cmath>

// The functions of ROS's angles package that smac_planner uses.
namespace angles
{
static inline double from_degrees(double degrees) {return degrees * M_PI / 180.0;}
static inline double to_degrees(double radians) {return radians * 180.0 / M_PI;}

static inline double normalize_angle_positive(double angle)
{
  const double result = std::fmod(angle, 2.0 * M_PI);
  if (result < 0) {
    return result + 2.0 * M_PI;
  }
  return result;
}

static inline double normalize_angle(double angle)
{
  const double result = std::fmod(angle + M_PI, 2.0 * M_PI);
  if (result <= 0.0) {
    return result + M_PI;
  }
  return result - M_PI;
}

static inline double shortest_angular_distance(double from, double to)
{
  return normalize_angle(to - from);
}
}  // namespace angles

#endif
