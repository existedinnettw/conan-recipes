cmake_minimum_required(VERSION 3.15)
project(sensorfusion LANGUAGES CXX)

find_package(vectorquaternionmatrix REQUIRED CONFIG)
# Build the reusable library only; upstream main.cpp is a PlatformIO demo.
add_library(sensorfusion src/src/SensorFusion.cpp)
target_compile_features(sensorfusion PUBLIC cxx_std_20)
target_include_directories(sensorfusion PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src/src>
    $<INSTALL_INTERFACE:include>
)
set_target_properties(sensorfusion PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
target_link_libraries(sensorfusion PUBLIC vectorquaternionmatrix::vectorquaternionmatrix)
include(GNUInstallDirs)
install(TARGETS sensorfusion
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(DIRECTORY src/src/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR} FILES_MATCHING PATTERN "*.h")
