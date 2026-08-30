cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(CANopenLinux REQUIRED CONFIG)

add_library(test_package STATIC test_package.c)
target_compile_features(test_package PRIVATE c_std_99)
target_compile_definitions(test_package PRIVATE CO_MULTIPLE_OD CO_SINGLE_THREAD)
target_link_libraries(test_package PRIVATE CANopenLinux::CANopenLinux)

