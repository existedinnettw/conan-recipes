cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(OpenFOAM REQUIRED CONFIG)

add_executable(test_package_cmake app/test_package.C)
set_source_files_properties(app/test_package.C PROPERTIES LANGUAGE CXX)
target_compile_features(test_package_cmake PRIVATE cxx_std_17)
target_link_libraries(test_package_cmake PRIVATE OpenFOAM::finiteVolume)
