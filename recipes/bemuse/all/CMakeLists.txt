# Builds BEMUse from BEMUSE_SRC_DIR as a library (everything but main.cpp) plus the
# BEMUse command-line program. Upstream's CMakeLists.txt points at a Windows Eigen
# path and forces -march=native, so it is not used.
cmake_minimum_required(VERSION 3.15)
project(BEMUse LANGUAGES CXX)

set(BEMUSE_SRC_DIR "" CACHE PATH "BEMUse source tree")
set(BEMUSE_PRECISION "SinglePrec" CACHE STRING "SinglePrec or DoublePrec")

find_package(Eigen3 REQUIRED CONFIG)
find_package(OpenMP REQUIRED)

set(_src "${BEMUSE_SRC_DIR}/src")
# Kernels.cpp and Geometry/Quadrule.cpp are #included by Panel.cpp and
# Geo_Elements.cpp; Boundary/Boundary.cpp is empty.
add_library(bemuse
  ${_src}/BEMUser_Console.cpp
  ${_src}/Boundary/Barge.cpp
  ${_src}/Boundary/Boundary_Base.cpp
  ${_src}/Boundary/Ellipsoid.cpp
  ${_src}/Boundary/GDF_Geo.cpp
  ${_src}/Boundary/Half_Volume_of_Revolution.cpp
  ${_src}/Boundary/Hoizontal_Volume_of_Revolution.cpp
  ${_src}/Boundary/MAR_Geo.cpp
  ${_src}/Boundary/STL_Geo.cpp
  ${_src}/Boundary/Ship_Hulls.cpp
  ${_src}/Boundary/Thin_Disc.cpp
  ${_src}/Boundary/Triple_Spar.cpp
  ${_src}/Boundary/Volume_of_Revolution.cpp
  ${_src}/Boundary/Wing.cpp
  ${_src}/Geometry/Geo_Elements.cpp
  ${_src}/Geometry/Panel.cpp
  ${_src}/Solver/Aerodynamic_Solver.cpp
  ${_src}/Solver/Hydrodynamic_Solver.cpp
  ${_src}/Solver/Hydrodynamic_Solver_IO.cpp
  ${_src}/Solver/Solver_Base.cpp
)
target_include_directories(bemuse PUBLIC
  $<BUILD_INTERFACE:${_src}>
  $<INSTALL_INTERFACE:include/BEMUse>
)
# The headers' Real/Vector/... typedefs depend on it.
target_compile_definitions(bemuse PUBLIC ${BEMUSE_PRECISION})
target_compile_features(bemuse PUBLIC cxx_std_17)
target_link_libraries(bemuse PUBLIC Eigen3::Eigen OpenMP::OpenMP_CXX)

add_executable(BEMUse ${BEMUSE_SRC_DIR}/main.cpp)
target_link_libraries(BEMUse PRIVATE bemuse)

include(GNUInstallDirs)
install(TARGETS bemuse BEMUse
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(DIRECTORY ${_src}/
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/BEMUse
  FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp"
)
