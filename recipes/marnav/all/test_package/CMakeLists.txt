cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

find_package(marnav REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_17)
target_link_libraries(test_package PRIVATE marnav::marnav)

if(TARGET marnav::marnav-io)
	target_link_libraries(test_package PRIVATE marnav::marnav-io)
	target_compile_definitions(test_package PRIVATE HAVE_MARNAV_IO)
endif()
