#include <smac_planner/a_star.hpp>
#include <smac_planner/collision_checker.hpp>
#include <smac_planner/node_hybrid.hpp>
#include <smac_planner/smoother.hpp>
#include <smac_planner/utils.hpp>

#include <cstdio>
#include <memory>

int main() {
  // 10 m x 10 m at 0.1 m, with a lethal island in the middle (as upstream's test_a_star_se2)
  costmap_2d::Costmap2D costmap(100, 100, 0.1, 0.0, 0.0, costmap_2d::FREE_SPACE);
  for (unsigned int i = 40; i <= 60; ++i) {
    for (unsigned int j = 40; j <= 60; ++j) {
      costmap.setCost(i, j, costmap_2d::LETHAL_OBSTACLE);
    }
  }

  const unsigned int size_theta = 72;
  smac_planner::GridCollisionChecker checker(&costmap, size_theta);
  checker.setFootprint(smac_planner::GridCollisionChecker::Footprint(), true, 0.0);

  smac_planner::SearchInfo info;
  info.change_penalty = 0.1;
  info.non_straight_penalty = 1.1;
  info.reverse_penalty = 2.0;
  info.minimum_turning_radius = 8;  // in grid cells
  info.retrospective_penalty = 0.015;
  info.analytic_expansion_max_length = 20.0;
  info.analytic_expansion_ratio = 3.5;
  info.cost_penalty = 1.7;

  smac_planner::AStarAlgorithm<smac_planner::NodeHybrid> a_star(smac_planner::MotionModel::DUBIN, info);
  int max_iterations = 10000;
  a_star.initialize(false, max_iterations, 10, 5000, 120.0, 401, size_theta);
  a_star.setCollisionChecker(&checker);
  a_star.setStart(10u, 10u, 0u);
  a_star.setGoal(80u, 80u, 40u);

  smac_planner::NodeHybrid::CoordinateVector path;
  int num_iterations = 0;
  const uint32_t result = a_star.createPath(path, num_iterations, 10.0, []() { return false; });
  if (result != mbf_msgs::GetPathResult::SUCCESS || path.empty()) {
    std::printf("no path found (result %u)\n", result);
    return 1;
  }
  for (const auto & pose : path) {
    if (costmap.getCost(pose.x, pose.y) != costmap_2d::FREE_SPACE) {
      std::printf("path crosses the obstacle at (%.1f, %.1f)\n", pose.x, pose.y);
      return 1;
    }
  }

  // Back to the world frame, start first, then smooth.
  nav_msgs::Path plan;
  for (auto it = path.rbegin(); it != path.rend(); ++it) {
    geometry_msgs::PoseStamped pose;
    pose.pose = smac_planner::Utils::getWorldCoords(it->x, it->y, &costmap);
    pose.pose.orientation = smac_planner::Utils::getWorldOrientation(
      smac_planner::NodeHybrid::motion_table.getAngleFromBin(static_cast<unsigned int>(it->theta)));
    plan.poses.push_back(pose);
  }
  smac_planner::Smoother smoother;
  smoother.initialize();
  smoother.setMinTurningRadius(info.minimum_turning_radius * costmap.getResolution());
  smoother.smooth(plan, &costmap, 0.5);

  std::printf("Hybrid-A* path with %zu poses after %d iterations, %.2f m long\n", path.size(), num_iterations,
              smac_planner::Utils::length(plan.poses));
  return 0;
}
