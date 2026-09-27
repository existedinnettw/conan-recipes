cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(OpenModelica REQUIRED CONFIG)

openmodelica_add_fmu(decay_fmu
  MODEL Decay
  SOURCES Decay.mo
  LIBRARIES Modelica
  FMI_VERSION 2.0
  FMU_TYPE cs
  NAME Decay)

# Unpack the FMU so the test can dlopen its binary and read its GUID.
set(fmu_dir "${CMAKE_CURRENT_BINARY_DIR}/Decay")
add_custom_command(
  OUTPUT "${fmu_dir}/modelDescription.xml"
  COMMAND "${CMAKE_COMMAND}" -E rm -rf "${fmu_dir}"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${fmu_dir}"
  COMMAND "${CMAKE_COMMAND}" -E chdir "${fmu_dir}" "${CMAKE_COMMAND}" -E tar xf "${decay_fmu_FMU_FILE}"
  DEPENDS "${decay_fmu_FMU_FILE}" decay_fmu
  VERBATIM)
add_custom_target(decay_fmu_unpacked ALL DEPENDS "${fmu_dir}/modelDescription.xml")

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE ${CMAKE_DL_LIBS})
add_dependencies(${PROJECT_NAME} decay_fmu_unpacked)
