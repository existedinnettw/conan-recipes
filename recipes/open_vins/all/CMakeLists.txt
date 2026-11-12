cmake_minimum_required(VERSION 3.15)
project(open_vins LANGUAGES CXX)

# Upstream ships one catkin/ament package per directory and, without ROS, compiles
# ov_core (and ov_init) into every library. This builds each package once and
# links them, so a consumer can use several of them together.

option(OPEN_VINS_WITH_ARUCO "Build ArUco tag tracking (needs opencv objdetect)" ON)

find_package(Eigen3 REQUIRED CONFIG)
find_package(OpenCV REQUIRED CONFIG)
find_package(Boost REQUIRED CONFIG)
find_package(Ceres REQUIRED CONFIG)

include(GNUInstallDirs)
set(OV_SRC ${CMAKE_CURRENT_SOURCE_DIR}/src)
set(OV_INCLUDE_DIR ${CMAKE_INSTALL_INCLUDEDIR}/open_vins)

function(ov_add_library name)
    cmake_parse_arguments(ARG "" "" "SOURCES;LIBS" ${ARGN})
    list(TRANSFORM ARG_SOURCES PREPEND ${OV_SRC}/${name}/src/)
    add_library(${name}_lib ${ARG_SOURCES})
    target_include_directories(${name}_lib PUBLIC
        $<BUILD_INTERFACE:${OV_SRC}/${name}/src>
        $<INSTALL_INTERFACE:${OV_INCLUDE_DIR}>)
    target_link_libraries(${name}_lib PUBLIC ${ARG_LIBS})
    target_compile_features(${name}_lib PUBLIC cxx_std_14)
    install(TARGETS ${name}_lib
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
    # Same merged header tree as upstream's non-ROS install.
    install(DIRECTORY ${OV_SRC}/${name}/src/
        DESTINATION ${OV_INCLUDE_DIR}
        FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp"
        PATTERN "ros" EXCLUDE
        PATTERN "plot" EXCLUDE)
endfunction()

set(OV_OPENCV_LIBS opencv_core opencv_imgproc opencv_imgcodecs opencv_features2d opencv_video opencv_calib3d)
if (OPEN_VINS_WITH_ARUCO)
    list(APPEND OV_OPENCV_LIBS opencv_objdetect)
endif ()

ov_add_library(ov_core
    SOURCES
        dummy.cpp
        cpi/CpiV1.cpp
        cpi/CpiV2.cpp
        sim/BsplineSE3.cpp
        track/TrackBase.cpp
        track/TrackAruco.cpp
        track/TrackDescriptor.cpp
        track/TrackKLT.cpp
        track/TrackSIM.cpp
        types/Landmark.cpp
        feat/Feature.cpp
        feat/FeatureDatabase.cpp
        feat/FeatureInitializer.cpp
        utils/print.cpp
    LIBS Eigen3::Eigen Boost::filesystem Boost::date_time Boost::headers ${OV_OPENCV_LIBS})
target_compile_definitions(ov_core_lib PUBLIC ROS_AVAILABLE=0 ENABLE_ARUCO_TAGS=$<BOOL:${OPEN_VINS_WITH_ARUCO}>)

ov_add_library(ov_init
    SOURCES
        dummy.cpp
        ceres/Factor_GenericPrior.cpp
        ceres/Factor_ImageReprojCalib.cpp
        ceres/Factor_ImuCPIv1.cpp
        ceres/State_JPLQuatLocal.cpp
        init/InertialInitializer.cpp
        dynamic/DynamicInitializer.cpp
        static/StaticInitializer.cpp
        sim/SimulatorInit.cpp
    LIBS ov_core_lib Ceres::ceres)

ov_add_library(ov_msckf
    SOURCES
        dummy.cpp
        sim/Simulator.cpp
        state/State.cpp
        state/StateHelper.cpp
        state/Propagator.cpp
        core/VioManager.cpp
        core/VioManagerHelper.cpp
        update/UpdaterHelper.cpp
        update/UpdaterMSCKF.cpp
        update/UpdaterSLAM.cpp
        update/UpdaterZeroVelocity.cpp
    LIBS ov_init_lib)

ov_add_library(ov_eval
    SOURCES
        dummy.cpp
        alignment/AlignTrajectory.cpp
        alignment/AlignUtils.cpp
        calc/ResultTrajectory.cpp
        calc/ResultSimulation.cpp
        utils/Loader.cpp
    LIBS ov_core_lib)
