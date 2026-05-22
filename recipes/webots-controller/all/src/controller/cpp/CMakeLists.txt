set(WEBOTS_CONTROLLER_CPP_SOURCE_DIR "${WEBOTS_REPO_SOURCE_DIR}/src/controller/cpp")

set(WEBOTS_CONTROLLER_CPP_SOURCES
    Accelerometer.cpp
    Altimeter.cpp
    Brake.cpp
    Camera.cpp
    Compass.cpp
    Connector.cpp
    Device.cpp
    Display.cpp
    DistanceSensor.cpp
    Emitter.cpp
    Field.cpp
    GPS.cpp
    Gyro.cpp
    InertialUnit.cpp
    Joystick.cpp
    Keyboard.cpp
    LED.cpp
    Lidar.cpp
    LightSensor.cpp
    Motion.cpp
    Motor.cpp
    Mouse.cpp
    Node.cpp
    Pen.cpp
    PositionSensor.cpp
    Proto.cpp
    Radar.cpp
    RangeFinder.cpp
    Receiver.cpp
    Robot.cpp
    Skin.cpp
    Speaker.cpp
    Supervisor.cpp
    TouchSensor.cpp
    VacuumGripper.cpp)

set(WEBOTS_CONTROLLER_CPP_SOURCE_PATHS)
foreach(_src IN LISTS WEBOTS_CONTROLLER_CPP_SOURCES)
  set(_candidate "${WEBOTS_CONTROLLER_CPP_SOURCE_DIR}/${_src}")
  if(EXISTS "${_candidate}")
    list(APPEND WEBOTS_CONTROLLER_CPP_SOURCE_PATHS "${_candidate}")
  endif()
endforeach()

file(GLOB_RECURSE WEBOTS_CONTROLLER_CPP_PUBLIC_HEADERS CONFIGURE_DEPENDS
     "${WEBOTS_REPO_SOURCE_DIR}/include/controller/cpp/webots/*.hpp")

add_library(webots_cpp_controller ${WEBOTS_CONTROLLER_CPP_SOURCE_PATHS})
add_library(webots-controller::webots_cpp_controller ALIAS
            webots_cpp_controller)
add_library(webots-controller::CppController ALIAS webots_cpp_controller)
add_library(webots-controller::webots-controller ALIAS webots_cpp_controller)

target_sources(
  webots_cpp_controller
  PUBLIC FILE_SET
         webots_cpp_headers
         TYPE
         HEADERS
         BASE_DIRS
         "${WEBOTS_REPO_SOURCE_DIR}/include/controller/cpp"
         FILES
         ${WEBOTS_CONTROLLER_CPP_PUBLIC_HEADERS})

if(WIN32)
  set_target_properties(webots_cpp_controller
                        PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

target_include_directories(
  webots_cpp_controller
  PUBLIC $<BUILD_INTERFACE:${WEBOTS_REPO_SOURCE_DIR}/include/controller/cpp>
         $<INSTALL_INTERFACE:include/controller/cpp>)

target_link_libraries(webots_cpp_controller PUBLIC webots_controller)

install(
  TARGETS webots_cpp_controller
  RUNTIME DESTINATION "bin"
  LIBRARY DESTINATION "lib"
  ARCHIVE DESTINATION "lib"
          FILE_SET webots_cpp_headers
          DESTINATION "include/controller/cpp")
