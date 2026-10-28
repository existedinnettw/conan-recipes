cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(usd-brep REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.cpp)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)
if(TARGET usd-brep::SM_API_USD)
  target_link_libraries(${PROJECT_NAME} PRIVATE usd-brep::SM_API_USD)
  target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_USD)
else()
  target_link_libraries(${PROJECT_NAME} PRIVATE usd-brep::SM_API)
endif()
