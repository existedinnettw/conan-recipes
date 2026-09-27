cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(OMSimulator REQUIRED CONFIG)
find_package(OpenModelica REQUIRED CONFIG)

openmodelica_add_fmu(decay_fmu
  MODEL Decay
  SOURCES Decay.mo
  LIBRARIES Modelica
  FMU_TYPE cs
  NAME Decay)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE OMSimulator::OMSimulator m)
target_compile_definitions(${PROJECT_NAME} PRIVATE DECAY_FMU="${decay_fmu_FMU_FILE}")
add_dependencies(${PROJECT_NAME} decay_fmu)
