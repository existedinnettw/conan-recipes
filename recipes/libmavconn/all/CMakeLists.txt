cmake_minimum_required(VERSION 3.15)
project(libmavconn LANGUAGES CXX)

find_package(asio REQUIRED CONFIG)
find_package(console_bridge REQUIRED CONFIG)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(MAVLINK_INCLUDE_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated/include/mavlink")
set(MAVLINK_GENERATOR "${CMAKE_CURRENT_SOURCE_DIR}/mavlink-source/pymavlink/tools/mavgen.py")
set(MAVLINK_XML "${CMAKE_CURRENT_SOURCE_DIR}/mavlink-source/message_definitions/v1.0/ardupilotmega.xml")
set(MAVLINK_DIALECT "${MAVLINK_INCLUDE_DIR}/v2.0/ardupilotmega/ardupilotmega.hpp")

add_custom_command(
  OUTPUT "${MAVLINK_DIALECT}"
  COMMAND ${CMAKE_COMMAND} -E env
    "PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}/mavlink-source"
    ${Python3_EXECUTABLE} "${MAVLINK_GENERATOR}"
    --lang=C++11 --wire-protocol=2.0 --no-validate
    "--output=${MAVLINK_INCLUDE_DIR}/v2.0" "${MAVLINK_XML}"
  DEPENDS "${MAVLINK_XML}" "${MAVLINK_GENERATOR}"
  VERBATIM
)

file(MAKE_DIRECTORY "${MAVLINK_INCLUDE_DIR}")
file(WRITE "${MAVLINK_INCLUDE_DIR}/config.h" "#define MAVLINK_VERSION \"2026.8.8\"\n")

add_library(mavconn
  "${CMAKE_CURRENT_SOURCE_DIR}/generated/mavlink_helpers.cpp"
  libmavconn/src/interface.cpp
  libmavconn/src/serial.cpp
  libmavconn/src/tcp.cpp
  libmavconn/src/udp.cpp
  "${MAVLINK_DIALECT}"
)
target_compile_features(mavconn PUBLIC cxx_std_20)
target_include_directories(mavconn
  PUBLIC
    "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/libmavconn/include>"
    "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/generated/include>"
    "$<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/generated/include>"
    "$<INSTALL_INTERFACE:include>"
)
target_link_libraries(mavconn PUBLIC asio::asio console_bridge::console_bridge)

install(TARGETS mavconn
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
install(DIRECTORY libmavconn/include/ DESTINATION include)
install(DIRECTORY generated/include/ DESTINATION include)
install(DIRECTORY "${MAVLINK_INCLUDE_DIR}/" DESTINATION include/mavlink)
