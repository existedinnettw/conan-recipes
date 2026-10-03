cmake_minimum_required(VERSION 3.15)
project(libcanard LANGUAGES C)

# Upstream ships only the sources (libcanard/canard.{c,h} plus the vendored
# lib/cavl2/cavl2.h, which canard.c includes privately); this builds and
# installs them.

set(CANARD_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
option(CANARD_CRC_TABLE "Use the 512-byte CRC lookup table instead of bitwise CRC" ON)

add_library(canard "${CANARD_UPSTREAM_DIR}/libcanard/canard.c")
target_include_directories(canard
  PUBLIC "${CANARD_UPSTREAM_DIR}/libcanard"
  PRIVATE "${CANARD_UPSTREAM_DIR}/lib/cavl2"
)
set_target_properties(canard PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)
if(CANARD_CRC_TABLE)
  target_compile_definitions(canard PRIVATE CANARD_CRC_TABLE=1)
else()
  target_compile_definitions(canard PRIVATE CANARD_CRC_TABLE=0)
endif()

include(GNUInstallDirs)
install(TARGETS canard
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(FILES "${CANARD_UPSTREAM_DIR}/libcanard/canard.h" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
