cmake_minimum_required(VERSION 3.15)
project(kdl_parser LANGUAGES CXX)

# Upstream only ships a catkin build. This file builds the same sources with
# plain CMake so that the package can be consumed without a ROS workspace.

option(KDL_PARSER_BUILD_TOOL "Build the check_kdl_parser command line tool" ON)

find_package(orocos_kdl REQUIRED CONFIG)
find_package(urdfdom REQUIRED CONFIG)
find_package(tinyxml REQUIRED CONFIG)
find_package(tinyxml2 REQUIRED CONFIG)

set(KDL_PARSER_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/kdl_parser")

add_library(kdl_parser "${KDL_PARSER_SOURCE_DIR}/src/kdl_parser.cpp")
target_compile_features(kdl_parser PUBLIC cxx_std_14)
target_include_directories(kdl_parser
  PUBLIC
    "$<BUILD_INTERFACE:${KDL_PARSER_SOURCE_DIR}/include>"
    "$<INSTALL_INTERFACE:include>"
)
target_link_libraries(kdl_parser
  PUBLIC
    orocos-kdl::orocos-kdl
    urdfdom::urdfdom
    tinyxml::tinyxml
    tinyxml2::tinyxml2
)

if(WIN32 AND BUILD_SHARED_LIBS)
  target_compile_definitions(kdl_parser PRIVATE KDL_PARSER_BUILDING_DLL)
endif()

install(TARGETS kdl_parser
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
install(DIRECTORY "${KDL_PARSER_SOURCE_DIR}/include/" DESTINATION include)

if(KDL_PARSER_BUILD_TOOL)
  add_executable(check_kdl_parser "${KDL_PARSER_SOURCE_DIR}/src/check_kdl_parser.cpp")
  target_link_libraries(check_kdl_parser PRIVATE kdl_parser)
  install(TARGETS check_kdl_parser RUNTIME DESTINATION bin)
endif()
