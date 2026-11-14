cmake_minimum_required(VERSION 3.15)
project(libchrony LANGUAGES C)

# Upstream builds with a plain Makefile driven by libtool; this mirrors its
# library target (client.c, message.c, socket.c) and install layout.
set(LIBCHRONY_SRC "${CMAKE_CURRENT_SOURCE_DIR}/src")

include(GNUInstallDirs)

add_library(chrony
    ${LIBCHRONY_SRC}/client.c
    ${LIBCHRONY_SRC}/message.c
    ${LIBCHRONY_SRC}/socket.c
)
target_include_directories(chrony PUBLIC
    $<BUILD_INTERFACE:${LIBCHRONY_SRC}>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_link_libraries(chrony PRIVATE m)
# libtool -version-info 0:1:0 -> libchrony.so.0.0.1
set_target_properties(chrony PROPERTIES
    C_STANDARD 99
    VERSION 0.0.1
    SOVERSION 0
    PUBLIC_HEADER ${LIBCHRONY_SRC}/chrony.h
)

install(TARGETS chrony
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
