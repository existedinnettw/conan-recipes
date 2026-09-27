cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

find_package(ECM REQUIRED NO_MODULE)
list(APPEND CMAKE_MODULE_PATH ${ECM_MODULE_PATH})
message(STATUS "ECM ${ECM_VERSION}")

include(ECMSetupVersion)
include(ECMGenerateHeaders)

ecm_setup_version(1.2.3
    VARIABLE_PREFIX TESTPKG
    VERSION_HEADER "${CMAKE_CURRENT_BINARY_DIR}/testpkg_version.h"
)

ecm_generate_headers(TESTPKG_FORWARDING_HEADERS
    HEADER_NAMES Foo
    OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/forward"
    REQUIRED_HEADERS TESTPKG_HEADERS
)

add_executable(test_package test_package.cpp)
target_include_directories(test_package PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}" "${CMAKE_CURRENT_BINARY_DIR}" "${CMAKE_CURRENT_BINARY_DIR}/forward")
