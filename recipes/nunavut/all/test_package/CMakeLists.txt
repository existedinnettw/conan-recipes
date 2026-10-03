cmake_minimum_required(VERSION 3.27)
project(test_package C)

find_package(Nunavut 3.0 REQUIRED CONFIG)

# Like protobuf_generate(): the headers are generated at build time and
# regenerated when a .dsdl file changes. uavcan.* is found in the public
# regulated namespace that the package ships (NUNAVUT_SUBMODULES_DIR).
add_cyphal_library(
    NAME demo
    LANGUAGE c
    LANGUAGE_STANDARD c11
    DSDL_FILES "${CMAKE_CURRENT_SOURCE_DIR}/dsdl/demo/Status.1.0.dsdl"
    DSDL_NAMESPACES "${CMAKE_CURRENT_SOURCE_DIR}/dsdl/demo"
    OUT_LIBRARY_TARGET demo_types
)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE ${demo_types})
set_target_properties(test_package PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)
