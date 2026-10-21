#ifndef SMAC_PLANNER_ROS_COMPAT_BASE_LOCAL_PLANNER_WORLD_MODEL_H
#define SMAC_PLANNER_ROS_COMPAT_BASE_LOCAL_PLANNER_WORLD_MODEL_H

#include <vector>

#include "geometry_msgs/Point.h"

namespace base_local_planner
{
// The overload of base_local_planner::WorldModel that CostmapModel implements; the
// others take ROS laser scans and polygons.
class WorldModel
{
public:
  virtual ~WorldModel() {}

  virtual double footprintCost(
    const geometry_msgs::Point & position, const std::vector<geometry_msgs::Point> & footprint,
    double inscribed_radius, double circumscribed_radius) = 0;
};
}  // namespace base_local_planner

#endif
