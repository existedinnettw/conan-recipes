#ifndef SMAC_PLANNER_ROS_COMPAT_TF_TF_H
#define SMAC_PLANNER_ROS_COMPAT_TF_TF_H

#include "geometry_msgs/Quaternion.h"
#include "tf2/utils.h"

namespace tf
{
inline geometry_msgs::Quaternion createQuaternionMsgFromYaw(double yaw)
{
  tf2::Quaternion q;
  q.setRPY(0.0, 0.0, yaw);
  return tf2::toMsg(q);
}

inline double getYaw(const geometry_msgs::Quaternion & q)
{
  return tf2::getYaw(q);
}
}  // namespace tf

#endif
