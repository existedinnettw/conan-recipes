# Replaces upstream's build, which hard-codes -march=native and -Werror and finds
# METIS and GKlib through install prefixes instead of package configs.
cmake_minimum_required(VERSION 3.15)
project(parmetis LANGUAGES C)

find_package(MPI REQUIRED CONFIG)
find_package(metis REQUIRED CONFIG)
find_package(gklib REQUIRED CONFIG)

file(GLOB parmetis_sources ${PARMETIS_SRC_DIR}/libparmetis/*.c)
add_library(parmetis ${parmetis_sources})
target_include_directories(parmetis
  PRIVATE ${PARMETIS_SRC_DIR}/libparmetis
  PUBLIC $<BUILD_INTERFACE:${PARMETIS_SRC_DIR}/include>)
# The flags upstream's conf/gkbuild.cmake adds for a release build.
target_compile_definitions(parmetis PRIVATE NDEBUG NDEBUG2 _FILE_OFFSET_BITS=64)
if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(parmetis PRIVATE -fno-strict-aliasing)
endif()
set_target_properties(parmetis PROPERTIES C_STANDARD 99)
target_link_libraries(parmetis PUBLIC MPI::MPI_C metis::metis PRIVATE gklib::gklib)
if(UNIX)
  target_link_libraries(parmetis PRIVATE m)
endif()

include(GNUInstallDirs)
install(TARGETS parmetis
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES ${PARMETIS_SRC_DIR}/include/parmetis.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
