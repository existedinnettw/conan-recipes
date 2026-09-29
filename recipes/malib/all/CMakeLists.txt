cmake_minimum_required(VERSION 3.15)
project(malib LANGUAGES C)

# Upstream only ships one makefile per application, each compiling the sources
# it needs straight into the executable. This builds them into one library
# instead, with the options of those makefiles.

set(MALIB_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
# ENA*, NFREQ, NEXOBS and TRACE: they size the structs in rtklib.h and switch
# its trace macros, so they are public; the recipe also hands them to consumers.
set(MALIB_PUBLIC_DEFINES "ENAGLO;ENAQZS;ENAGAL;ENACMP;ENAIRN;NFREQ=5;NEXOBS=5;TRACE"
  CACHE STRING "Compile definitions consumers of rtklib.h must share")
option(MALIB_BUILD_TOOLS "Build the console applications" ON)

include(GNUInstallDirs)
find_package(Threads REQUIRED)

file(GLOB malib_sources "${MALIB_UPSTREAM_DIR}/src/*.c" "${MALIB_UPSTREAM_DIR}/src/rcv/*.c")

# postpos.c and rtksvr.c call showmsg(), settspan() and settime(), which each
# application is expected to define. Provide no-op fallbacks, each in its own
# object, so the linker only takes the ones an application lacks.
set(stub_dir "${CMAKE_CURRENT_BINARY_DIR}/app_stubs")
foreach(stub IN ITEMS
    "int showmsg(const char *format, ...) { (void)format; return 0; }"
    "void settspan(gtime_t ts, gtime_t te) { (void)ts; (void)te; }"
    "void settime(gtime_t time) { (void)time; }")
  string(REGEX MATCH "[a-z]+\\(" stub_name "${stub}")
  string(REPLACE "(" "" stub_name "${stub_name}")
  file(WRITE "${stub_dir}/${stub_name}.c" "#include \"rtklib.h\"\n${stub}\n")
  list(APPEND malib_sources "${stub_dir}/${stub_name}.c")
endforeach()

add_library(malib ${malib_sources})
target_include_directories(malib PUBLIC
  "$<BUILD_INTERFACE:${MALIB_UPSTREAM_DIR}/src>"
  "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>"
)
target_compile_definitions(malib
  PUBLIC ${MALIB_PUBLIC_DEFINES}
  # postpos.c writes PROGNAME into the header of solution files; the makefiles
  # set it to the application's name.
  PRIVATE SVR_REUSEADDR "PROGNAME=\"MALIB\""
)
target_link_libraries(malib PUBLIC m Threads::Threads)

install(TARGETS malib
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(FILES "${MALIB_UPSTREAM_DIR}/src/rtklib.h" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

if(MALIB_BUILD_TOOLS)
  set(app_dir "${MALIB_UPSTREAM_DIR}/app/consapp")
  # rnx2rtkp.c defines PROGNAME itself.
  add_executable(rnx2rtkp "${app_dir}/rnx2rtkp/rnx2rtkp.c")
  add_executable(recvbias "${app_dir}/recvbias/recvbias.c")
  target_compile_definitions(recvbias PRIVATE "PROGNAME=\"recvbias\"")
  add_executable(rtkrcv "${app_dir}/rtkrcv/rtkrcv.c" "${app_dir}/rtkrcv/vt.c")
  target_include_directories(rtkrcv PRIVATE "${app_dir}/rtkrcv")
  target_compile_definitions(rtkrcv PRIVATE "PROGNAME=\"rtkrcv\"")
  foreach(tool IN ITEMS rnx2rtkp recvbias rtkrcv)
    target_link_libraries(${tool} PRIVATE malib)
  endforeach()
  install(TARGETS rnx2rtkp recvbias rtkrcv RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
