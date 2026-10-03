cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(dronecan-libcanard REQUIRED CONFIG)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE dronecan-libcanard::canard)
if(WITH_SOCKETCAN)
  target_compile_definitions(test_package PRIVATE WITH_SOCKETCAN)
endif()
