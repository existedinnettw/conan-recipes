cmake_minimum_required(VERSION 3.15)
project(dronecan_libcanard LANGUAGES C)

# Upstream's CMakeLists only builds the unit tests (it forces -Werror and
# fetches googletest) and has no install rules, so the library is built here.

set(CANARD_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
option(CANARD_WITH_SOCKETCAN "Build the Linux SocketCAN driver into the library" OFF)

add_library(canard "${CANARD_UPSTREAM_DIR}/canard.c")
target_include_directories(canard PUBLIC "${CANARD_UPSTREAM_DIR}")
set_target_properties(canard PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)
# canard.h sizes its structures from these, so the consumer gets the same values
# through package_info().
foreach(flag IN ITEMS CANARD_ENABLE_CANFD CANARD_MULTI_IFACE CANARD_ENABLE_DEADLINE)
  if(${flag})
    target_compile_definitions(canard PUBLIC ${flag}=1)
  endif()
endforeach()

set(public_headers "${CANARD_UPSTREAM_DIR}/canard.h")
if(CANARD_WITH_SOCKETCAN)
  target_sources(canard PRIVATE "${CANARD_UPSTREAM_DIR}/drivers/socketcan/socketcan.c")
  list(APPEND public_headers "${CANARD_UPSTREAM_DIR}/drivers/socketcan/socketcan.h")
endif()

if(WIN32 AND BUILD_SHARED_LIBS)
  set_target_properties(canard PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

include(GNUInstallDirs)
install(TARGETS canard
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(FILES ${public_headers} DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
# Header-only C++ wrappers (Canard::Publisher, Canard::Subscriber, ...) over the
# headers that dronecan_dsdlc generates.
install(DIRECTORY "${CANARD_UPSTREAM_DIR}/canard/"
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/canard
  FILES_MATCHING PATTERN "*.h"
  PATTERN "tests" EXCLUDE
)
