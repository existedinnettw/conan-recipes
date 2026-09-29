cmake_minimum_required(VERSION 3.15)
project(rtklib LANGUAGES C)

# Replaces upstream's CMakeLists, which always builds a shared library, installs
# it as a RUNTIME into lib/, installs no header, and also pulls in CTest, CPack
# and the Qt GUIs whenever it finds Qt.

set(RTKLIB_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
# ENA*, NFREQ, NEXOBS and TRACE: they size the structs in rtklib.h and switch
# its trace macros, so they are public; the recipe also hands them to consumers.
set(RTKLIB_PUBLIC_DEFINES "ENAGLO;ENAQZS;ENAGAL;ENACMP;ENAIRN;NFREQ=3;NEXOBS=3;TRACE"
  CACHE STRING "Compile definitions consumers of rtklib.h must share")
option(RTKLIB_BUILD_TOOLS "Build the console applications" ON)

include(GNUInstallDirs)
find_package(Threads REQUIRED)

file(GLOB rtklib_sources "${RTKLIB_UPSTREAM_DIR}/src/*.c")
# src/rcv also holds decoders upstream no longer builds (comnav.c, tersus.c,
# ...), which no longer compile against rtklib.h.
foreach(rcv IN ITEMS binex crescent javad novatel nvs rt17 septentrio skytraq swiftnav ublox unicore)
  list(APPEND rtklib_sources "${RTKLIB_UPSTREAM_DIR}/src/rcv/${rcv}.c")
endforeach()

# rtkcmn.c defines no-op showmsg(), settspan() and settime() for applications
# that do not, but only when built as a DLL (-DDLL/-DWIN_DLL), and then in the
# same object as everything else in rtkcmn.c: an application that defines one
# of them gets a duplicate symbol against a static library. Give each fallback
# its own object instead, so the linker only takes the ones the application
# lacks, whether the library is static or shared.
set(rtklib_windows_dll OFF)
if(MSVC AND BUILD_SHARED_LIBS)
  # WIN_DLL also selects __declspec(dllexport) and brings rtkcmn.c's own
  # fallbacks; a DLL resolves its calls internally, so those are enough.
  set(rtklib_windows_dll ON)
else()
  set(stub_dir "${CMAKE_CURRENT_BINARY_DIR}/app_stubs")
  foreach(stub IN ITEMS
      "int showmsg(const char *format, ...) { (void)format; return 0; }"
      "void settspan(gtime_t ts, gtime_t te) { (void)ts; (void)te; }"
      "void settime(gtime_t time) { (void)time; }")
    string(REGEX MATCH "[a-z]+\\(" stub_name "${stub}")
    string(REPLACE "(" "" stub_name "${stub_name}")
    file(WRITE "${stub_dir}/${stub_name}.c" "#include \"rtklib.h\"\n${stub}\n")
    list(APPEND rtklib_sources "${stub_dir}/${stub_name}.c")
  endforeach()
endif()

add_library(rtklib ${rtklib_sources})
# ublox.c defines its own bool, which C23 (GCC 15's default) makes a keyword.
set_target_properties(rtklib PROPERTIES C_STANDARD 99)
target_include_directories(rtklib PUBLIC
  "$<BUILD_INTERFACE:${RTKLIB_UPSTREAM_DIR}/src>"
  "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>"
)
target_compile_definitions(rtklib
  PUBLIC ${RTKLIB_PUBLIC_DEFINES}
  PRIVATE SVR_REUSEADDR
)
if(WIN32)
  # rtklib.h tests WIN32, which MinGW does not predefine in strict ISO mode.
  target_compile_definitions(rtklib PUBLIC WIN32)
  if(rtklib_windows_dll)
    target_compile_definitions(rtklib PRIVATE WIN_DLL)
  elseif(MSVC)
    # Otherwise rtklib.h declares everything __declspec(dllimport).
    target_compile_definitions(rtklib PUBLIC WIN_STATIC)
  endif()
  if(MSVC)
    target_compile_definitions(rtklib PRIVATE _CRT_SECURE_NO_WARNINGS)
  endif()
  target_link_libraries(rtklib PUBLIC ws2_32 winmm)
else()
  target_link_libraries(rtklib PUBLIC m)
endif()
target_link_libraries(rtklib PUBLIC Threads::Threads)

install(TARGETS rtklib
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(FILES "${RTKLIB_UPSTREAM_DIR}/src/rtklib.h" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

if(RTKLIB_BUILD_TOOLS)
  set(app_dir "${RTKLIB_UPSTREAM_DIR}/app/consapp")
  set(tools rnx2rtkp convbin pos2kml)
  add_executable(rnx2rtkp "${app_dir}/rnx2rtkp/rnx2rtkp.c")
  add_executable(convbin "${app_dir}/convbin/convbin.c")
  add_executable(pos2kml "${app_dir}/pos2kml/pos2kml.c")
  if(UNIX)
    # vt.c is termios based.
    add_executable(rtkrcv "${app_dir}/rtkrcv/rtkrcv.c" "${app_dir}/rtkrcv/vt.c")
    target_include_directories(rtkrcv PRIVATE "${app_dir}/rtkrcv")
    add_executable(str2str "${app_dir}/str2str/str2str.c")
    list(APPEND tools rtkrcv str2str)
  endif()
  foreach(tool IN LISTS tools)
    target_link_libraries(${tool} PRIVATE rtklib)
  endforeach()
  install(TARGETS ${tools} RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
