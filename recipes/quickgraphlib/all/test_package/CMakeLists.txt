cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Quick)
# QuickGraphLib is QML only; find_package() checks the package is consumable.
find_package(quickgraphlib REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_17)
target_link_libraries(test_package PRIVATE quickgraphlib::quickgraphlib Qt6::Gui Qt6::Qml Qt6::Quick)
