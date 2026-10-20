cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(canopen-stack REQUIRED CONFIG)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE canopen-stack::canopen-stack)
set_target_properties(test_package PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)
