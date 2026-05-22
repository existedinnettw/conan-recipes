cmake_minimum_required(VERSION 3.23)
project(test_package C CXX)

find_package(webots-controller REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE webots-controller::CppController)

add_executable(test_package_c test_package.c)
target_link_libraries(test_package_c PRIVATE webots-controller::Controller)

if(POLICY CMP0207)
  cmake_policy(SET CMP0207 NEW)
endif()

set(_extra_runtime_dirs)
if(CMAKE_PREFIX_PATH)
  foreach(prefix IN LISTS CMAKE_PREFIX_PATH)
    list(APPEND _extra_runtime_dirs "${prefix}/lib")
  endforeach()
endif()
if(WIN32 AND DEFINED ENV{MINGW_HOME})
  list(APPEND _extra_runtime_dirs "$ENV{MINGW_HOME}/bin")
endif()

# Webots controllers rely on seeing shared deps in the same directory as the
# executable. Destination therefore change to "."
install(
  TARGETS test_package test_package_c RUNTIME_DEPENDENCY_SET
          test_package_runtime_deps
  RUNTIME DESTINATION .
  LIBRARY DESTINATION .
  ARCHIVE DESTINATION .)

if(WIN32)
  set(_runtime_dep_pre_excludes "^api-ms-win-.*" "^ext-ms-.*")
  set(_runtime_dep_post_excludes ".*/system32/.*" ".*/Windows/.*"
                                 ".*/SysWOW64/.*")
else()
  set(_runtime_dep_pre_excludes
      [[libc\.so\..*]] [[libgcc_s\.so\..*]] [[libm\.so\..*]]
      [[libstdc\+\+\.so\..*]] [[ld-linux-x86-64\.so\..*]])
  set(_runtime_dep_post_excludes [[^/lib.*]] [[^/usr/lib.*]])
endif()

install(
  RUNTIME_DEPENDENCY_SET
  test_package_runtime_deps
  PRE_EXCLUDE_REGEXES
  ${_runtime_dep_pre_excludes}
  POST_EXCLUDE_REGEXES
  ${_runtime_dep_post_excludes}
  DIRECTORIES
  ${CONAN_RUNTIME_LIB_DIRS}
  ${CMAKE_SYSROOT}/lib
  ${_extra_runtime_dirs}
  DESTINATION
  .)
