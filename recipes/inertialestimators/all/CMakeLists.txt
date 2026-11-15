cmake_minimum_required(VERSION 3.15)
project(inertialestimators LANGUAGES CXX)

find_package(matlib REQUIRED CONFIG)
add_library(inertialestimators
    src/Cpp/src/AHRS_Attitude_EKF.cpp
    src/Cpp/src/AHRS_Attitude_SO3.cpp
    src/Cpp/src/AHRS_EKF_AV.cpp
    src/Cpp/src/AHRS_Madgwick.cpp
    src/Cpp/src/IMU_EKF_AV.cpp
    src/Cpp/src/IMU_Madgwick.cpp
)
target_include_directories(inertialestimators PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src/Cpp/inc>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(inertialestimators PUBLIC cxx_std_11)
target_link_libraries(inertialestimators PUBLIC matlib::matlib)
set_target_properties(inertialestimators PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
include(GNUInstallDirs)
install(TARGETS inertialestimators
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(DIRECTORY src/Cpp/inc/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
