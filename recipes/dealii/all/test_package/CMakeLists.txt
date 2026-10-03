cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

# The same calls deal.II's tutorials make.
find_package(deal.II REQUIRED CONFIG)
deal_ii_initialize_cached_variables()

add_executable(test_package test_package.cc)
target_compile_features(test_package PRIVATE cxx_std_17)
deal_ii_setup_target(test_package)
