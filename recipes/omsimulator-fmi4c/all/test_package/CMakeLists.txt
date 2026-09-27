cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(omsimulator-fmi4c REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE omsimulator-fmi4c::fmi4c)

# A zip archive to read back through the miniunz component.
set(fmu "${CMAKE_CURRENT_BINARY_DIR}/test.fmu")
add_custom_command(
  OUTPUT "${fmu}"
  COMMAND "${CMAKE_COMMAND}" -E tar cf "${fmu}" --format=zip modelDescription.xml
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/modelDescription.xml"
  VERBATIM)
add_custom_target(test_fmu ALL DEPENDS "${fmu}")
add_dependencies(${PROJECT_NAME} test_fmu)
target_compile_definitions(${PROJECT_NAME} PRIVATE TEST_FMU="${fmu}")
