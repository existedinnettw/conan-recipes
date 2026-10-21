cmake_minimum_required(VERSION 3.15)
project(smac_planner LANGUAGES CXX)

# Upstream's CMakeLists.txt is a catkin package that builds the move_base_flex
# Hybrid-A* plugin. Build only the planning code (A*, the 2D, Hybrid-A* and
# State Lattice nodes, analytic expansion, collision checking, costmap
# downsampling and smoothing) as a library here, against the header shims in
# ros_compat/ and the costmap_2d::Costmap2D and base_local_planner::CostmapModel
# sources of rapyuta-robotics' ROS navigation fork. The smac_planner_*.cpp
# plugins are left out.

set(SMAC_PLANNER_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
set(NAVIGATION_DIR "${SMAC_PLANNER_UPSTREAM_DIR}/navigation")
set(ROS_COMPAT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/ros_compat")

find_package(ompl REQUIRED CONFIG)
find_package(Boost REQUIRED CONFIG)
find_package(nlohmann_json REQUIRED CONFIG)

add_library(smac_planner
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/a_star.cpp
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/analytic_expansion.cpp
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/collision_checker.cpp
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/costmap_downsampler.cpp
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/node_2d.cpp
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/node_basic.cpp
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/node_hybrid.cpp
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/node_lattice.cpp
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/smoother.cpp
  ${SMAC_PLANNER_UPSTREAM_DIR}/src/types.cpp
  ${NAVIGATION_DIR}/costmap_2d/src/costmap_2d.cpp
  ${NAVIGATION_DIR}/costmap_2d/src/costmap_math.cpp
  ${NAVIGATION_DIR}/base_local_planner/src/costmap_model.cpp
)
target_include_directories(smac_planner PUBLIC
  "$<BUILD_INTERFACE:${SMAC_PLANNER_UPSTREAM_DIR}/include>"
  "$<BUILD_INTERFACE:${ROS_COMPAT_DIR}>"
  "$<BUILD_INTERFACE:${NAVIGATION_DIR}/costmap_2d/include>"
  "$<BUILD_INTERFACE:${NAVIGATION_DIR}/base_local_planner/include>"
)
target_link_libraries(smac_planner PUBLIC
  ompl::ompl
  Boost::headers
  Boost::thread
  nlohmann_json::nlohmann_json
)
target_compile_features(smac_planner PUBLIC cxx_std_17)

include(GNUInstallDirs)
install(TARGETS smac_planner
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(DIRECTORY "${SMAC_PLANNER_UPSTREAM_DIR}/include/smac_planner"
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
  FILES_MATCHING PATTERN "*.hpp" PATTERN "*.h"
  # the move_base_flex plugins, which are not built
  PATTERN "smac_planner_*.hpp" EXCLUDE
)
# The shims and the ROS navigation headers keep their ROS include paths
# (geometry_msgs/Pose.h, costmap_2d/costmap_2d.h, ...), so they get their own
# include directory to stay out of the way of a real ROS installation.
set(ROS_COMPAT_INSTALL_DIR ${CMAKE_INSTALL_INCLUDEDIR}/smac_planner/ros_compat)
install(DIRECTORY "${ROS_COMPAT_DIR}/"
  DESTINATION ${ROS_COMPAT_INSTALL_DIR}
  FILES_MATCHING PATTERN "*.h"
)
install(FILES
  "${NAVIGATION_DIR}/costmap_2d/include/costmap_2d/costmap_2d.h"
  "${NAVIGATION_DIR}/costmap_2d/include/costmap_2d/costmap_math.h"
  "${NAVIGATION_DIR}/costmap_2d/include/costmap_2d/cost_values.h"
  DESTINATION ${ROS_COMPAT_INSTALL_DIR}/costmap_2d
)
install(FILES
  "${NAVIGATION_DIR}/base_local_planner/include/base_local_planner/costmap_model.h"
  "${NAVIGATION_DIR}/base_local_planner/include/base_local_planner/line_iterator.h"
  DESTINATION ${ROS_COMPAT_INSTALL_DIR}/base_local_planner
)
install(DIRECTORY "${SMAC_PLANNER_UPSTREAM_DIR}/lattice_primitives/sample_primitives"
  DESTINATION ${CMAKE_INSTALL_DATADIR}/smac_planner
)
