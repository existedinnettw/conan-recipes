cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(g2o REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE g2o::core g2o::types_sba g2o::solver_eigen)
if(TARGET g2o::solver_csparse)
    target_link_libraries(${PROJECT_NAME} PRIVATE g2o::solver_csparse)
    target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_CSPARSE)
endif()
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_14)
