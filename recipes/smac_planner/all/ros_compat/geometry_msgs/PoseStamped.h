#ifndef SMAC_PLANNER_ROS_COMPAT_GEOMETRY_MSGS_POSESTAMPED_H
#define SMAC_PLANNER_ROS_COMPAT_GEOMETRY_MSGS_POSESTAMPED_H

#include "geometry_msgs/Pose.h"
#include "std_msgs/Header.h"

namespace geometry_msgs
{
struct PoseStamped
{
  std_msgs::Header header;
  Pose pose;
};

inline bool operator==(const PoseStamped & a, const PoseStamped & b)
{
  return a.header == b.header && a.pose == b.pose;
}
inline bool operator!=(const PoseStamped & a, const PoseStamped & b) {return !(a == b);}
}  // namespace geometry_msgs

#endif
