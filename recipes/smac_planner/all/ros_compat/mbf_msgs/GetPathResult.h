#ifndef SMAC_PLANNER_ROS_COMPAT_MBF_MSGS_GETPATHRESULT_H
#define SMAC_PLANNER_ROS_COMPAT_MBF_MSGS_GETPATHRESULT_H

#include <cstdint>

namespace mbf_msgs
{
// Outcome codes of move_base_flex's mbf_msgs/action/GetPath.action.
struct GetPathResult
{
  static constexpr uint8_t SUCCESS = 0;
  static constexpr uint8_t FAILURE = 50;
  static constexpr uint8_t CANCELED = 51;
  static constexpr uint8_t INVALID_START = 52;
  static constexpr uint8_t INVALID_GOAL = 53;
  static constexpr uint8_t BLOCKED_START = 54;
  static constexpr uint8_t BLOCKED_GOAL = 55;
  static constexpr uint8_t NO_PATH_FOUND = 56;
  static constexpr uint8_t PAT_EXCEEDED = 57;
  static constexpr uint8_t EMPTY_PATH = 58;
  static constexpr uint8_t TF_ERROR = 59;
  static constexpr uint8_t NOT_INITIALIZED = 60;
  static constexpr uint8_t INVALID_PLUGIN = 61;
  static constexpr uint8_t INTERNAL_ERROR = 62;
  static constexpr uint8_t OUT_OF_MAP = 63;
  static constexpr uint8_t MAP_ERROR = 64;
  static constexpr uint8_t STOPPED = 65;
};
}  // namespace mbf_msgs

#endif
