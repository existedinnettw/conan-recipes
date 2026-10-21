#ifndef SMAC_PLANNER_ROS_COMPAT_STD_MSGS_HEADER_H
#define SMAC_PLANNER_ROS_COMPAT_STD_MSGS_HEADER_H

#include <cstdint>
#include <string>

#include "ros/time.h"

namespace std_msgs
{
struct Header
{
  uint32_t seq{0};
  ros::Time stamp;
  std::string frame_id;
};

inline bool operator==(const Header & a, const Header & b)
{
  return a.seq == b.seq && a.stamp == b.stamp && a.frame_id == b.frame_id;
}
inline bool operator!=(const Header & a, const Header & b) {return !(a == b);}
}  // namespace std_msgs

#endif
