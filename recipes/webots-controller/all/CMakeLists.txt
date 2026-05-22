cmake_minimum_required(VERSION 3.23)
project(webots_controller LANGUAGES C CXX)

option(WEBOTS_CONTROLLER_NO_PLUGINS "Disable runtime plugin loading (dlopen/LoadLibrary paths)." ON)

if(NOT DEFINED WEBOTS_REPO_SOURCE_DIR)
  set(WEBOTS_REPO_SOURCE_DIR "")
endif()

if(WEBOTS_REPO_SOURCE_DIR STREQUAL "")
  message(FATAL_ERROR "WEBOTS_REPO_SOURCE_DIR must point to cloned Webots repository")
endif()

if(MSVC)
  find_package(dirent CONFIG REQUIRED)

  file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/cmake")
  file(
    DOWNLOAD
    https://github.com/cpm-cmake/CPM.cmake/releases/download/v0.40.8/CPM.cmake
    "${CMAKE_CURRENT_BINARY_DIR}/cmake/CPM.cmake"
    EXPECTED_HASH
      SHA256=78ba32abdf798bc616bab7c73aac32a17bbd7b06ad9e26a6add69de8f3ae4791)
  include("${CMAKE_CURRENT_BINARY_DIR}/cmake/CPM.cmake")

  CPMAddPackage(
    NAME libunistd
    GITHUB_REPOSITORY robinrowe/libunistd
    GIT_TAG v1.4
    DOWNLOAD_ONLY YES)

  add_library(webots_controller_msvc_unix_headers INTERFACE)
  target_include_directories(
    webots_controller_msvc_unix_headers
    SYSTEM
    INTERFACE "$<TARGET_PROPERTY:dirent::dirent,INTERFACE_INCLUDE_DIRECTORIES>"
              "${libunistd_SOURCE_DIR}/unistd")
  target_link_libraries(webots_controller_msvc_unix_headers
                        INTERFACE dirent::dirent)
  target_compile_definitions(webots_controller_msvc_unix_headers
                             INTERFACE _CRT_DECLARE_NONSTDC_NAMES=0)
  target_compile_options(webots_controller_msvc_unix_headers
                         INTERFACE /FIunistd.h)
endif()

add_subdirectory(src/controller)