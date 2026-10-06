# Builds the AirLib client library and MavLinkCom from an AirSim source tree
# (Cosys-AirSim and its forks), replacing upstream's cmake/ folder, which expects
# rpclib and Eigen copied into the tree by setup.sh and only builds static libraries.
cmake_minimum_required(VERSION 3.15)
project(AirSim LANGUAGES CXX)

find_package(Threads REQUIRED)
find_package(rpclib REQUIRED CONFIG)
find_package(Eigen3 REQUIRED CONFIG)

set(AIRSIM_ROOT "${CMAKE_CURRENT_SOURCE_DIR}")

# MavLinkCom
file(GLOB MAVLINKCOM_SOURCES
  "${AIRSIM_ROOT}/MavLinkCom/common_utils/*.cpp"
  "${AIRSIM_ROOT}/MavLinkCom/src/*.cpp"
  "${AIRSIM_ROOT}/MavLinkCom/src/impl/*.cpp"
  "${AIRSIM_ROOT}/MavLinkCom/src/serial_com/*.cpp"
)
if(WIN32)
  list(APPEND MAVLINKCOM_SOURCES "${AIRSIM_ROOT}/MavLinkCom/src/impl/windows/WindowsFindSerialPorts.cpp")
else()
  list(APPEND MAVLINKCOM_SOURCES "${AIRSIM_ROOT}/MavLinkCom/src/impl/linux/MavLinkFindSerialPorts.cpp")
endif()

add_library(MavLinkCom ${MAVLINKCOM_SOURCES})
target_compile_features(MavLinkCom PUBLIC cxx_std_17)
target_include_directories(MavLinkCom
  PUBLIC
    "$<BUILD_INTERFACE:${AIRSIM_ROOT}/MavLinkCom/include>"
    "$<INSTALL_INTERFACE:include/MavLinkCom>"
  PRIVATE
    "${AIRSIM_ROOT}/MavLinkCom"
    "${AIRSIM_ROOT}/MavLinkCom/common_utils"
)
target_link_libraries(MavLinkCom PUBLIC Threads::Threads)
if(WIN32)
  target_link_libraries(MavLinkCom PUBLIC ws2_32 wbemuuid ole32 oleaut32 setupapi cfgmgr32)
endif()

# AirLib: the RPC client (and server) API plus the vehicle API implementations.
# Everything else in AirLib (physics, sensors, firmwares) is header-only.
file(GLOB_RECURSE AIRLIB_SOURCES "${AIRSIM_ROOT}/AirLib/src/*.cpp")

add_library(AirLib ${AIRLIB_SOURCES})
target_compile_features(AirLib PUBLIC cxx_std_17)
target_include_directories(AirLib
  PUBLIC
    "$<BUILD_INTERFACE:${AIRSIM_ROOT}/AirLib/include>"
    "$<INSTALL_INTERFACE:include/AirLib>"
)
target_link_libraries(AirLib PUBLIC MavLinkCom rpclib::rpc Eigen3::Eigen Threads::Threads)

install(TARGETS MavLinkCom AirLib
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
install(DIRECTORY "${AIRSIM_ROOT}/MavLinkCom/include/" DESTINATION include/MavLinkCom)
install(DIRECTORY "${AIRSIM_ROOT}/AirLib/include/" DESTINATION include/AirLib)
