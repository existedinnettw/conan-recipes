cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(CANopenLinux REQUIRED CONFIG)

set(OD_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(OD_C "${OD_DIR}/OD.c")
set(OD_H "${OD_DIR}/OD.h")

add_custom_command(
    OUTPUT "${OD_C}" "${OD_H}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${OD_DIR}"
    COMMAND
        "${EDSSharp_EXECUTABLE}"
        --infile "${TEST_OD_INPUT}"
        --outfile "${OD_C}"
        --type CanOpenNodeV4
    DEPENDS "${TEST_OD_INPUT}"
    COMMENT "Generating OD.c and OD.h"
    VERBATIM
)

add_executable(test_package test_package.c "${OD_C}")
target_compile_features(test_package PRIVATE c_std_99)
target_compile_definitions(test_package PRIVATE CO_MULTIPLE_OD CO_SINGLE_THREAD)
target_include_directories(test_package BEFORE PRIVATE "${OD_DIR}")
target_link_libraries(test_package PRIVATE CANopenLinux::CANopenLinux)
