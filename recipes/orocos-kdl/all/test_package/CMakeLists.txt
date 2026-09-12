cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(orocos_kdl REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_14)
target_link_libraries(test_package PRIVATE orocos-kdl::orocos-kdl)
