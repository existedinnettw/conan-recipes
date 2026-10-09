cmake_minimum_required(VERSION 3.15)
project(nanospline LANGUAGES CXX)

# Upstream's CMakeLists fetches Eigen, Catch2 and sanitizers-cmake with CPM and
# builds its tests with -Werror; this builds only the forward declaration
# library, which holds explicit instantiations of the generated inflection,
# singularity and tangent matching code.

set(NANOSPLINE_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")

find_package(Eigen3 REQUIRED CONFIG)

file(GLOB NANOSPLINE_SOURCES "${NANOSPLINE_UPSTREAM_DIR}/src/*.cpp")
add_library(nanospline STATIC ${NANOSPLINE_SOURCES})
target_include_directories(nanospline PUBLIC "${NANOSPLINE_UPSTREAM_DIR}/include")
target_link_libraries(nanospline PUBLIC Eigen3::Eigen)
target_compile_features(nanospline PUBLIC cxx_std_20)
if(NANOSPLINE_SYMPY)
  target_compile_definitions(nanospline PUBLIC NANOSPLINE_SYMPY)
endif()
if(MSVC)
  target_compile_definitions(nanospline PUBLIC _USE_MATH_DEFINES)
  target_compile_options(nanospline PUBLIC /bigobj)
endif()

include(GNUInstallDirs)
install(TARGETS nanospline ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(DIRECTORY "${NANOSPLINE_UPSTREAM_DIR}/include/nanospline" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
