set(WEBOTS_HEADERS_ROOT "${WEBOTS_REPO_SOURCE_DIR}/include/controller/c")
set(WEBOTS_INCLUDE_ROOT "${WEBOTS_REPO_SOURCE_DIR}/include")
set(WEBOTS_STB_DIR "${WEBOTS_REPO_SOURCE_DIR}/src/stb")
set(WEBOTS_CONTROLLER_C_SOURCE_DIR "${WEBOTS_REPO_SOURCE_DIR}/src/controller/c")

file(GLOB_RECURSE WEBOTS_CONTROLLER_C_PUBLIC_HEADERS CONFIGURE_DEPENDS
     "${WEBOTS_HEADERS_ROOT}/webots/*.h")
file(GLOB_RECURSE WEBOTS_CONTROLLER_PLUGIN_PUBLIC_HEADERS CONFIGURE_DEPENDS
     "${WEBOTS_INCLUDE_ROOT}/plugins/*.h")

set(WEBOTS_CONTROLLER_C_CORE_SOURCES
    abstract_camera.c
    accelerometer.c
    altimeter.c
    ansi_codes.c
    base64.c
    brake.c
    camera.c
    compass.c
    connector.c
    console.c
    default_robot_window.c
    device.c
    display.c
    distance_sensor.c
    emitter.c
    file.c
    g_image.c
    g_pipe.c
    gps.c
    gyro.c
    image.c
    inertial_unit.c
    joystick.c
    keyboard.c
    led.c
    lidar.c
    light_sensor.c
    microphone.c
    motion.c
    motor.c
    mouse.c
    node.c
    pen.c
    percent.c
    position_sensor.c
    radar.c
    range_finder.c
    receiver.c
    request.c
    robot.c
    scheduler.c
    sha1.c
    skin.c
    speaker.c
    string.c
    supervisor.c
    system.c
    tcp_client.c
    touch_sensor.c
    vacuum_gripper.c)

set(WEBOTS_CONTROLLER_C_PLUGIN_SOURCES dynamic_library.c html_robot_window.c
                                       radio.c remote_control.c robot_window.c)

set(WEBOTS_CONTROLLER_C_SOURCES ${WEBOTS_CONTROLLER_C_CORE_SOURCES})
list(APPEND WEBOTS_CONTROLLER_C_SOURCES ${WEBOTS_CONTROLLER_C_PLUGIN_SOURCES})

list(TRANSFORM WEBOTS_CONTROLLER_C_SOURCES PREPEND "${WEBOTS_CONTROLLER_C_SOURCE_DIR}/")

if(MSVC)
  find_package(Git REQUIRED)
  set(WEBOTS_CONTROLLER_MSVC_SOURCE_DIR
      "${CMAKE_CURRENT_BINARY_DIR}/msvc-patched-source")
  file(REMOVE_RECURSE "${WEBOTS_CONTROLLER_MSVC_SOURCE_DIR}")
  file(COPY "${WEBOTS_CONTROLLER_C_SOURCE_DIR}/"
       DESTINATION "${WEBOTS_CONTROLLER_MSVC_SOURCE_DIR}")
  file(RELATIVE_PATH WEBOTS_CONTROLLER_MSVC_SOURCE_RELATIVE_DIR
       "${CMAKE_SOURCE_DIR}" "${WEBOTS_CONTROLLER_MSVC_SOURCE_DIR}")
  execute_process(
    COMMAND
      "${GIT_EXECUTABLE}" apply
      "--directory=${WEBOTS_CONTROLLER_MSVC_SOURCE_RELATIVE_DIR}"
      "${CMAKE_SOURCE_DIR}/patches/msvc-controller-c.patch"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    RESULT_VARIABLE WEBOTS_CONTROLLER_MSVC_PATCH_RESULT)
  if(NOT WEBOTS_CONTROLLER_MSVC_PATCH_RESULT EQUAL 0)
    message(FATAL_ERROR "Failed to apply MSVC controller C source patch")
  endif()

  list(TRANSFORM WEBOTS_CONTROLLER_C_SOURCES
       REPLACE "^${WEBOTS_CONTROLLER_C_SOURCE_DIR}" "${WEBOTS_CONTROLLER_MSVC_SOURCE_DIR}")
endif()

add_library(webots_controller ${WEBOTS_CONTROLLER_C_SOURCES})
add_library(webots-controller::webots_controller ALIAS webots_controller)
add_library(webots-controller::Controller ALIAS webots_controller)

target_sources(
  webots_controller
  PUBLIC FILE_SET
         webots_c_headers
         TYPE
         HEADERS
         BASE_DIRS
         "${WEBOTS_HEADERS_ROOT}"
         FILES
         ${WEBOTS_CONTROLLER_C_PUBLIC_HEADERS}
         FILE_SET
         webots_plugin_headers
         TYPE
         HEADERS
         BASE_DIRS
         "${WEBOTS_INCLUDE_ROOT}"
         FILES
         ${WEBOTS_CONTROLLER_PLUGIN_PUBLIC_HEADERS})

if(WIN32)
  set_target_properties(webots_controller PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS
                                                     ON)
  target_link_libraries(webots_controller PRIVATE ws2_32)
endif()

if(MSVC)
  target_sources(webots_controller
                 PRIVATE "${libunistd_SOURCE_DIR}/unistd/clock_gettime.cpp")
  target_link_libraries(webots_controller
                        PRIVATE webots_controller_msvc_unix_headers)
  target_compile_definitions(webots_controller PRIVATE _USE_MATH_DEFINES
                                                       O_TEXT=_O_TEXT)
  target_compile_options(webots_controller PRIVATE /utf-8)
endif()

target_include_directories(
  webots_controller
  PUBLIC $<BUILD_INTERFACE:${WEBOTS_INCLUDE_ROOT}>
         $<BUILD_INTERFACE:${WEBOTS_HEADERS_ROOT}> $<INSTALL_INTERFACE:include>
         $<INSTALL_INTERFACE:include/controller/c>
  PRIVATE ${WEBOTS_STB_DIR} ${WEBOTS_CONTROLLER_C_SOURCE_DIR}
          ${WEBOTS_CONTROLLER_MSVC_SOURCE_DIR})

target_compile_definitions(
  webots_controller PRIVATE LIBCONTROLLER_VERSION="${LIBCONTROLLER_VERSION}")
if(WEBOTS_CONTROLLER_NO_PLUGINS)
  target_compile_definitions(webots_controller
                             PUBLIC WEBOTS_CONTROLLER_NO_PLUGINS=1)
endif()

if(UNIX)
  target_link_libraries(webots_controller PRIVATE m)
  if(NOT APPLE)
    target_link_libraries(webots_controller PRIVATE pthread rt)
    if(NOT WEBOTS_CONTROLLER_NO_PLUGINS)
      target_link_libraries(webots_controller PRIVATE dl)
    endif()
  endif()
endif()

install(
  TARGETS webots_controller
  RUNTIME DESTINATION "bin"
  LIBRARY DESTINATION "lib"
  ARCHIVE DESTINATION "lib"
          FILE_SET webots_c_headers
          DESTINATION "include/controller/c"
          FILE_SET webots_plugin_headers
          DESTINATION "include")
