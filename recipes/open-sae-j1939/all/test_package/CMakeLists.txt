cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(OpenSAEJ1939 REQUIRED CONFIG)

add_executable(test_package test_package.c)
target_compile_features(test_package PRIVATE c_std_90)
target_link_libraries(test_package PRIVATE OpenSAEJ1939::opensaej1939)
