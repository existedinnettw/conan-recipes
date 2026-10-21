cmake_minimum_required(VERSION 3.15)
project(hybrid_astar LANGUAGES CXX)

# Upstream's CMakeLists.txt is a catkin package that builds the ROS node. Build
# only the search, collision checking and smoothing as a library here; the ROS
# node (planner, path, visualize, main, tf_broadcaster) is left out.

set(HYBRID_ASTAR_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")

find_package(ompl REQUIRED CONFIG)
find_package(Boost REQUIRED CONFIG)

add_library(hybrid_astar
  ${HYBRID_ASTAR_UPSTREAM_DIR}/src/algorithm.cpp
  ${HYBRID_ASTAR_UPSTREAM_DIR}/src/node2d.cpp
  ${HYBRID_ASTAR_UPSTREAM_DIR}/src/node3d.cpp
  ${HYBRID_ASTAR_UPSTREAM_DIR}/src/collisiondetection.cpp
  ${HYBRID_ASTAR_UPSTREAM_DIR}/src/smoother.cpp
  ${HYBRID_ASTAR_UPSTREAM_DIR}/src/dubins.cpp
  ${HYBRID_ASTAR_UPSTREAM_DIR}/src/dynamicvoronoi.cpp
  ${HYBRID_ASTAR_UPSTREAM_DIR}/src/bucketedqueue.cpp
)
# The headers include each other by bare name; consumers use <hybrid_astar/...>.
target_include_directories(hybrid_astar PRIVATE "${HYBRID_ASTAR_UPSTREAM_DIR}/include")
target_link_libraries(hybrid_astar PUBLIC ompl::ompl PRIVATE Boost::headers)
target_compile_features(hybrid_astar PUBLIC cxx_std_17)
set_target_properties(hybrid_astar PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)

include(GNUInstallDirs)
install(TARGETS hybrid_astar
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
foreach(header algorithm bucketedqueue collisiondetection constants dubins dynamicvoronoi
               gradient helper lookup node2d node3d point smoother vector2d)
  install(FILES "${HYBRID_ASTAR_UPSTREAM_DIR}/include/${header}.h"
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/hybrid_astar
  )
endforeach()
