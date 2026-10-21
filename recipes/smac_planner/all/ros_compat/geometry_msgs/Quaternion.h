#ifndef SMAC_PLANNER_ROS_COMPAT_GEOMETRY_MSGS_QUATERNION_H
#define SMAC_PLANNER_ROS_COMPAT_GEOMETRY_MSGS_QUATERNION_H

namespace geometry_msgs
{
// Zero-initialized like the ROS message, so w is 0 until set.
struct Quaternion
{
  double x{0.0};
  double y{0.0};
  double z{0.0};
  double w{0.0};
};

inline bool operator==(const Quaternion & a, const Quaternion & b)
{
  return a.x == b.x && a.y == b.y && a.z == b.z && a.w == b.w;
}
inline bool operator!=(const Quaternion & a, const Quaternion & b) {return !(a == b);}
}  // namespace geometry_msgs

#endif
