cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(SCOTCH REQUIRED CONFIG)

add_executable(test_package test_package.c)
target_compile_features(test_package PRIVATE c_std_99)
if(WITH_PTSCOTCH)
  target_compile_definitions(test_package PRIVATE WITH_PTSCOTCH)
  target_link_libraries(test_package PRIVATE SCOTCH::ptscotch)
else()
  target_link_libraries(test_package PRIVATE SCOTCH::scotch)
endif()
