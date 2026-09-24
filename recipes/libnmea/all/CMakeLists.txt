cmake_minimum_required(VERSION 3.15)
project(libnmea LANGUAGES C)

# Builds libnmea in upstream's "static parsers" mode: every parser module is
# compiled into the one library instead of being dlopen()ed from a hard-coded
# install prefix at runtime, so the package is relocatable and works without a
# dynamic loader. Upstream's CMakeLists only supports this for a static
# library and renames the per-parser entry points with objcopy; renaming them
# with the preprocessor instead also allows a shared library.

set(LIBNMEA_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
set(LIBNMEA_PARSERS "" CACHE STRING "Semicolon-separated parser modules to build in")

if(NOT LIBNMEA_PARSERS)
  message(FATAL_ERROR "LIBNMEA_PARSERS must name at least one parser")
endif()

add_library(nmea
  "${LIBNMEA_UPSTREAM_DIR}/src/nmea/nmea.c"
  "${LIBNMEA_UPSTREAM_DIR}/src/nmea/parser_static.c"
  "${LIBNMEA_UPSTREAM_DIR}/src/parsers/parse.c"
)
target_include_directories(nmea PRIVATE "${LIBNMEA_UPSTREAM_DIR}/src/nmea")

list(LENGTH LIBNMEA_PARSERS parser_count)
target_compile_definitions(nmea PRIVATE PARSER_COUNT=${parser_count})

set(public_headers "${LIBNMEA_UPSTREAM_DIR}/src/nmea/nmea.h")
set(parser_headers "")
foreach(parser IN LISTS LIBNMEA_PARSERS)
  set(parser_src "${LIBNMEA_UPSTREAM_DIR}/src/parsers/${parser}.c")
  if(NOT EXISTS "${parser_src}")
    message(FATAL_ERROR "Unknown libnmea parser: ${parser}")
  endif()
  target_sources(nmea PRIVATE "${parser_src}")
  string(TOUPPER "${parser}" parser_upper)
  target_compile_definitions(nmea PRIVATE ENABLE_${parser_upper})
  set(renames "")
  foreach(fn IN ITEMS init parse set_default allocate_data free_data)
    list(APPEND renames "${fn}=nmea_${parser}_${fn}")
  endforeach()
  set_source_files_properties("${parser_src}" PROPERTIES COMPILE_DEFINITIONS "${renames}")
  list(APPEND parser_headers "${LIBNMEA_UPSTREAM_DIR}/src/parsers/${parser}.h")
endforeach()

include(GNUInstallDirs)
install(TARGETS nmea
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(FILES ${public_headers} DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES ${parser_headers} DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/nmea)
