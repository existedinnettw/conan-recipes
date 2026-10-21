#ifndef SMAC_PLANNER_ROS_COMPAT_GEOMETRY_MSGS_POSE_H
#define SMAC_PLANNER_ROS_COMPAT_GEOMETRY_MSGS_POSE_H

#include "geometry_msgs/Point.h"
#include "geometry_msgs/Quaternion.h"

namespace geometry_msgs
{
struct Pose
{
  Point position;
  Quaternion orientation;
};

inline bool operator==(const Pose & a, const Pose & b)
{
  return a.position == b.position && a.orientation == b.orientation;
}
inline bool operator!=(const Pose & a, const Pose & b) {return !(a == b);}
}  // namespace geometry_msgs

#endif
