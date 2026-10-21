Minimal stand-ins for the ROS 1 headers that smac_planner's planning code
includes, so the algorithms build without ROS. Only what that code uses is
here: plain message structs, tf2/tf yaw and quaternion helpers, angles, the
move_base_flex GetPath result codes, logging macros printing to stderr and a
wall-clock ros::Time.

costmap_2d::Costmap2D and base_local_planner::CostmapModel are the sources of
rapyuta-robotics' ROS navigation fork (see conandata.yml); the costmap_2d/footprint.h and
base_local_planner/world_model.h here replace the ROS-heavy originals with the
one function and base class those sources need.
