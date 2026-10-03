cmake_minimum_required(VERSION 3.27)
project(test_package C)

find_package(libudpard REQUIRED CONFIG)
find_package(Nunavut 3.0 REQUIRED CONFIG)

add_cyphal_library(
    NAME heartbeat
    LANGUAGE c
    LANGUAGE_STANDARD c11
    DSDL_FILES "${NUNAVUT_SUBMODULES_DIR}/public_regulated_data_types/uavcan/node/7509.Heartbeat.1.0.dsdl"
    OUT_LIBRARY_TARGET heartbeat_types
)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE libudpard::udpard ${heartbeat_types})
set_target_properties(test_package PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)
