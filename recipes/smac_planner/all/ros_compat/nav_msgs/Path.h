#ifndef SMAC_PLANNER_ROS_COMPAT_NAV_MSGS_PATH_H
#define SMAC_PLANNER_ROS_COMPAT_NAV_MSGS_PATH_H

#include <vector>

#include "geometry_msgs/PoseStamped.h"
#include "std_msgs/Header.h"

namespace nav_msgs
{
struct Path
{
  std_msgs::Header header;
  std::vector<geometry_msgs::PoseStamped> poses;
};
}  // namespace nav_msgs

#endif
