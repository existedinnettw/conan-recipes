#ifndef SMAC_PLANNER_ROS_COMPAT_GEOMETRY_MSGS_POINT_H
#define SMAC_PLANNER_ROS_COMPAT_GEOMETRY_MSGS_POINT_H

namespace geometry_msgs
{
struct Point
{
  double x{0.0};
  double y{0.0};
  double z{0.0};
};

inline bool operator==(const Point & a, const Point & b)
{
  return a.x == b.x && a.y == b.y && a.z == b.z;
}
inline bool operator!=(const Point & a, const Point & b) {return !(a == b);}
}  // namespace geometry_msgs

#endif
