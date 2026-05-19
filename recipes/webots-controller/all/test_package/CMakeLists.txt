cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(webots-controller REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE Webots::CppController)

if(POLICY CMP0207)
  cmake_policy(SET CMP0207 NEW)
endif()

# Webots controllers rely on seeing shared deps in the same directory as the executable.
install(TARGETS test_package
  RUNTIME_DEPENDENCY_SET test_package_runtime_deps
  RUNTIME DESTINATION bin
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib)

if(WIN32)
  # for single-config generators.
  set(_runtime_dependency_directories)
  string(TOUPPER "${CMAKE_BUILD_TYPE}" _conan_build_type)
  set(_webots_bin_dirs_var "webots-controller_BIN_DIRS_${_conan_build_type}")
  if(DEFINED ${_webots_bin_dirs_var})
    list(APPEND _runtime_dependency_directories ${${_webots_bin_dirs_var}})
  endif()
  if(DEFINED ENV{MINGW_HOME})
    list(APPEND _runtime_dependency_directories "$ENV{MINGW_HOME}/bin")
  endif()
  install(
    RUNTIME_DEPENDENCY_SET test_package_runtime_deps
    DIRECTORIES ${_runtime_dependency_directories}
    PRE_EXCLUDE_REGEXES
      "^api-ms-win-.*"
      "^ext-ms-.*"
    POST_EXCLUDE_REGEXES
      ".*/system32/.*"
      ".*/Windows/.*"
      ".*/SysWOW64/.*"
    DESTINATION bin)
else()
  install(
    RUNTIME_DEPENDENCY_SET test_package_runtime_deps
    DESTINATION bin)
endif()
