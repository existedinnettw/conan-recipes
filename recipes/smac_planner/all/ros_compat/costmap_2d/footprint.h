#ifndef SMAC_PLANNER_ROS_COMPAT_COSTMAP_2D_FOOTPRINT_H
#define SMAC_PLANNER_ROS_COMPAT_COSTMAP_2D_FOOTPRINT_H

#include <algorithm>
#include <limits>
#include <vector>

#include "costmap_2d/costmap_math.h"
#include "geometry_msgs/Point.h"

namespace costmap_2d
{
// From costmap_2d/src/footprint.cpp; the rest of footprint.h needs ROS parameters and messages.
inline void calculateMinAndMaxDistances(
  const std::vector<geometry_msgs::Point> & footprint, double & min_dist, double & max_dist)
{
  min_dist = std::numeric_limits<double>::max();
  max_dist = 0.0;

  if (footprint.size() <= 2) {
    return;
  }

  for (unsigned int i = 0; i < footprint.size() - 1; ++i) {
    // check the distance from the robot center point to the first vertex
    double vertex_dist = distance(0.0, 0.0, footprint[i].x, footprint[i].y);
    double edge_dist = distanceToLine(
      0.0, 0.0, footprint[i].x, footprint[i].y, footprint[i + 1].x, footprint[i + 1].y);
    min_dist = std::min(min_dist, std::min(vertex_dist, edge_dist));
    max_dist = std::max(max_dist, std::max(vertex_dist, edge_dist));
  }

  // we also need to do the last vertex and the first vertex
  double vertex_dist = distance(0.0, 0.0, footprint.back().x, footprint.back().y);
  double edge_dist = distanceToLine(
    0.0, 0.0, footprint.back().x, footprint.back().y, footprint.front().x, footprint.front().y);
  min_dist = std::min(min_dist, std::min(vertex_dist, edge_dist));
  max_dist = std::max(max_dist, std::max(vertex_dist, edge_dist));
}
}  // namespace costmap_2d

#endif
