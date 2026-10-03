cmake_minimum_required(VERSION 3.15)
project(libudpard LANGUAGES C)

# Upstream's CMakeLists only builds the unit tests; this builds and installs
# libudpard/udpard.{c,h}. _udpard_cavl.h is private to udpard.c.

set(UDPARD_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")

add_library(udpard "${UDPARD_UPSTREAM_DIR}/libudpard/udpard.c")
target_include_directories(udpard PUBLIC "${UDPARD_UPSTREAM_DIR}/libudpard")
set_target_properties(udpard PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)

if(WIN32 AND BUILD_SHARED_LIBS)
  set_target_properties(udpard PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

include(GNUInstallDirs)
install(TARGETS udpard
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(FILES "${UDPARD_UPSTREAM_DIR}/libudpard/udpard.h" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
