cmake_minimum_required(VERSION 3.15)
project(omsimulator_fmi4c LANGUAGES C)

# Builds OpenModelica's fmi4c fork from OMSimulator-3rdParty on top of the minizip
# package. fmi4c and OMSimulator unzip through OMSimulator's modified copies of minizip's
# command line programs (miniunz(), minizip(), miniunz_onefile_to_memory()), built here
# as the "miniunz" library. The rest of 3rdParty/minizip/src (unzip.c, zip.c, and copies
# of zlib.h, unzip.h, ...) is left out, so the packaged minizip and zlib headers are used.

include(GNUInstallDirs)

set(THIRD_PARTY "${CMAKE_CURRENT_SOURCE_DIR}/src")

find_package(minizip REQUIRED CONFIG)

add_library(miniunz "${THIRD_PARTY}/minizip/src/miniunz.c" "${THIRD_PARTY}/minizip/src/minizip.c")
set(miniunz_headers "${THIRD_PARTY}/minizip/src/miniunz.h" "${THIRD_PARTY}/minizip/src/minizip.h")
file(COPY ${miniunz_headers} DESTINATION "${CMAKE_CURRENT_BINARY_DIR}/miniunz/include")
target_include_directories(miniunz PUBLIC "$<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/miniunz/include>")
target_link_libraries(miniunz PUBLIC minizip::minizip)

set(FMI4C_BUILD_SHARED ${BUILD_SHARED_LIBS})
set(FMI4C_USE_SYSTEM_ZIP OFF)
set(FMI4C_USE_EXTERNAL_MINIZIP ON)
set(FMI4C_EXTERNAL_MINIZIP miniunz CACHE STRING "")
add_subdirectory("${THIRD_PARTY}/fmi4c" fmi4c)

# Upstream installs the headers, but not the library when minizip is external.
install(TARGETS miniunz fmi4c
        RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"
        LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
        ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(FILES ${miniunz_headers} DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}")
