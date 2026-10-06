# Builds O3DE's core framework libraries (AzCore, AzNetworking, AzFramework) from the
# engine source tree, replacing O3DE's own build system, which needs the whole engine,
# a downloaded Python and its prebuilt 3rdParty packages.
# The source and compile settings mirror Code/Framework/*/CMakeLists.txt and
# cmake/Platform/{Common,Linux}/Configurations_*.cmake.
cmake_minimum_required(VERSION 3.22)
project(O3DE LANGUAGES C CXX)

set(O3DE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/o3de")
set(O3DE_RAPIDXML_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/rapidxml/RapidXML/include")
set(O3DE_CONFIGURATION "profile" CACHE STRING "O3DE build configuration: debug, profile or release")
set(O3DE_PYTHONPATH "" CACHE STRING "Python path holding jinja2 for cmake/AzAutoGen.py")
option(O3DE_WITH_XCB "Linux: native windows and keyboard/mouse input through XCB" ON)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  set(PAL Linux)
  set(pal linux)
else()
  message(FATAL_ERROR "Only Linux is supported")
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(Threads REQUIRED)
find_package(lua REQUIRED CONFIG)
find_package(RapidJSON REQUIRED CONFIG)
find_package(ZLIB REQUIRED CONFIG)
find_package(zstd REQUIRED CONFIG)
find_package(lz4 REQUIRED CONFIG)
find_package(cityhash REQUIRED CONFIG)
find_package(OpenSSL REQUIRED CONFIG)
find_package(libunwind REQUIRED CONFIG)
# Conan's zstd and lz4 name their targets after the library type.
foreach(target zstd::libzstd_static zstd::libzstd_shared)
  if(TARGET ${target})
    set(ZSTD_TARGET ${target})
  endif()
endforeach()
foreach(target LZ4::lz4_static LZ4::lz4_shared)
  if(TARGET ${target})
    set(LZ4_TARGET ${target})
  endif()
endforeach()
if(O3DE_WITH_XCB)
  find_package(xorg REQUIRED CONFIG)
  find_package(xkbcommon REQUIRED CONFIG)
  find_package(PkgConfig REQUIRED)
  # Not among xorg/system's components.
  pkg_check_modules(XCB_XINPUT REQUIRED IMPORTED_TARGET xcb-xinput)
endif()

# Settings every O3DE target and every consumer compiles with.
add_library(o3de_config INTERFACE)
target_compile_features(o3de_config INTERFACE cxx_std_20)
target_compile_definitions(o3de_config INTERFACE LINUX LINUX64)
if(O3DE_CONFIGURATION STREQUAL "debug")
  target_compile_definitions(o3de_config INTERFACE _DEBUG AZ_DEBUG_BUILD AZ_ENABLE_TRACING AZ_ENABLE_DEBUG_TOOLS)
elseif(O3DE_CONFIGURATION STREQUAL "profile")
  target_compile_definitions(o3de_config INTERFACE _PROFILE AZ_PROFILE_BUILD NDEBUG AZ_ENABLE_TRACING AZ_ENABLE_DEBUG_TOOLS)
elseif(O3DE_CONFIGURATION STREQUAL "release")
  target_compile_definitions(o3de_config INTERFACE _RELEASE RELEASE AZ_RELEASE_BUILD NDEBUG)
else()
  message(FATAL_ERROR "Unknown O3DE_CONFIGURATION '${O3DE_CONFIGURATION}'")
endif()
# AZStd::pair's conditional explicit (C++20 explicit(bool)) trips GCC 15 like it trips
# Clang 18 and older, for which upstream sets this define (Configurations_clang.cmake).
# Upstream: "This feature is not necessary for O3DE to actually function".
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU"
   OR (CMAKE_CXX_COMPILER_ID STREQUAL "Clang" AND CMAKE_CXX_COMPILER_VERSION VERSION_LESS 19.0))
  target_compile_definitions(o3de_config INTERFACE O3DE_DISABLE_CONDITIONAL_EXPLICIT=1)
endif()
if(NOT BUILD_SHARED_LIBS)
  target_compile_definitions(o3de_config INTERFACE AZ_MONOLITHIC_BUILD)
endif()
if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64")
  # The SIMD math headers use SSE4.1 intrinsics.
  target_compile_options(o3de_config INTERFACE -msse4.1)
endif()

# Settings only O3DE's own sources compile with.
add_library(o3de_private INTERFACE)
target_compile_definitions(o3de_private INTERFACE AZ_BUILD_CONFIGURATION_TYPE="${O3DE_CONFIGURATION}")
# Not for shared libraries: with GCC, hidden visibility also hides the EBus template
# instantiations AzCore exports (AZ_INSTANTIATE_EBUS_*), and AzFramework fails to link.
if(NOT BUILD_SHARED_LIBS)
  target_compile_options(o3de_private INTERFACE -fvisibility=hidden $<$<COMPILE_LANGUAGE:CXX>:-fvisibility-inlines-hidden>)
endif()

# Upstream's Lua package puts the headers in a Lua/ folder; Conan's lua does not, and
# does not install the internal lobject.h, which AzCore only includes for LUAI_MAXALIGN.
set(O3DE_LUA_SHIM_DIR "${CMAKE_CURRENT_BINARY_DIR}/lua-shim")
foreach(header lua.h lualib.h lauxlib.h)
  file(WRITE "${O3DE_LUA_SHIM_DIR}/Lua/${header}" "#pragma once\n#include <${header}>\n")
endforeach()
file(WRITE "${O3DE_LUA_SHIM_DIR}/Lua/lobject.h" [=[
#pragma once
#include <lua.h>
#if !defined(LUAI_MAXALIGN)
#define LUAI_MAXALIGN lua_Number n; double u; void *s; lua_Integer i; long l
#endif
]=])

# Reads O3DE *_files.cmake lists, whose paths are relative to the list file.
function(o3de_read_files out)
  set(result)
  foreach(list_file IN LISTS ARGN)
    unset(FILES)
    include("${list_file}")
    cmake_path(GET list_file PARENT_PATH list_dir)
    foreach(file IN LISTS FILES)
      cmake_path(ABSOLUTE_PATH file BASE_DIRECTORY "${list_dir}" NORMALIZE OUTPUT_VARIABLE file)
      list(APPEND result "${file}")
    endforeach()
  endforeach()
  set(${out} ${result} PARENT_SCOPE)
endfunction()

# cmake/LyAutoGen.cmake's ly_add_autogen: generates sources from the target's
# xml/json/jinja files with cmake/AzAutoGen.py.
function(o3de_add_autogen target project_dir rules)
  get_target_property(all_files ${target} SOURCES)
  set(input_files ${all_files})
  list(FILTER input_files INCLUDE REGEX ".*\\.(xml|json|jinja)$")
  set(input_files_path "${CMAKE_CURRENT_BINARY_DIR}/Azcg/Temp/${target}_input_files.txt")
  file(WRITE "${input_files_path}" "${input_files}")
  set(output_dir "${CMAKE_CURRENT_BINARY_DIR}/Azcg/Generated/${target}")
  set(autogen
    "${CMAKE_COMMAND}" -E env "PYTHONPATH=${O3DE_PYTHONPATH}"
    "${Python3_EXECUTABLE}" "${O3DE_ROOT}/cmake/AzAutoGen.py")
  # The rules are one argument, a ;-separated list.
  string(REPLACE ";" "\\;" rules "${rules}")
  set(args "${target}" "${CMAKE_BINARY_DIR}/Azcg/TemplateCache/" "${output_dir}/" "${project_dir}" "${input_files_path}" "${rules}")
  execute_process(
    COMMAND ${autogen} ${args} -n
    OUTPUT_VARIABLE outputs
    ERROR_VARIABLE error
    RESULT_VARIABLE result
  )
  if(NOT result EQUAL 0)
    message(FATAL_ERROR "AutoGen expansion rules failed for target ${target}:\n${error}")
  endif()
  string(STRIP "${outputs}" outputs)
  add_custom_command(
    OUTPUT ${outputs}
    DEPENDS ${input_files} "${O3DE_ROOT}/cmake/AzAutoGen.py"
    COMMAND ${autogen} --prune ${args}
    COMMENT "Running AutoGen for ${target}"
    VERBATIM
  )
  target_sources(${target} PRIVATE ${outputs})
  target_include_directories(${target} PUBLIC "$<BUILD_INTERFACE:${output_dir}>")
endfunction()

# AzCore
set(AZCORE_DIR "${O3DE_ROOT}/Code/Framework/AzCore")
o3de_read_files(azcore_sources
  "${AZCORE_DIR}/AzCore/azcore_files.cmake"
  "${AZCORE_DIR}/AzCore/std/azstd_files.cmake"
  "${AZCORE_DIR}/Platform/${PAL}/platform_${pal}_files.cmake"
)
add_library(AzCore ${azcore_sources})
target_compile_definitions(AzCore PRIVATE AZCORE_EXPORTS)
target_include_directories(AzCore PUBLIC
  "$<BUILD_INTERFACE:${AZCORE_DIR};${AZCORE_DIR}/Platform/${PAL};${AZCORE_DIR}/Platform/Common>"
  "$<BUILD_INTERFACE:${O3DE_LUA_SHIM_DIR};${O3DE_RAPIDXML_INCLUDE_DIR}>"
  "$<INSTALL_INTERFACE:include/O3DE>"
)
# cmake/Configurations.cmake's default
set_source_files_properties(
  "${AZCORE_DIR}/AzCore/Memory/OSAllocator.cpp"
  "${AZCORE_DIR}/AzCore/Memory/PoolAllocator.cpp"
  "${AZCORE_DIR}/AzCore/Memory/SystemAllocator.cpp"
  PROPERTIES COMPILE_DEFINITIONS O3DE_STACK_CAPTURE_DEPTH=3
)
target_link_libraries(AzCore
  PUBLIC o3de_config lua::lua rapidjson ZLIB::ZLIB ${ZSTD_TARGET} cityhash::cityhash Threads::Threads ${CMAKE_DL_LIBS}
  PRIVATE o3de_private libunwind::libunwind atomic
)

# AzNetworking (always static upstream)
set(AZNETWORKING_DIR "${O3DE_ROOT}/Code/Framework/AzNetworking")
o3de_read_files(aznetworking_sources
  "${AZNETWORKING_DIR}/AzNetworking/aznetworking_files.cmake"
  "${AZNETWORKING_DIR}/Platform/${PAL}/platform_${pal}_files.cmake"
)
add_library(AzNetworking STATIC ${aznetworking_sources})
set_target_properties(AzNetworking PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(AzNetworking PUBLIC
  "$<BUILD_INTERFACE:${AZNETWORKING_DIR};${AZNETWORKING_DIR}/Platform/Common;${AZNETWORKING_DIR}/Platform/${PAL}>"
  "$<INSTALL_INTERFACE:include/O3DE>"
)
target_link_libraries(AzNetworking
  PUBLIC AzCore rapidjson
  PRIVATE o3de_private ${ZSTD_TARGET} openssl::openssl
)
o3de_add_autogen(AzNetworking "${AZNETWORKING_DIR}"
  "*.AutoPackets.xml,AutoPackets_Header.jinja,$path/$fileprefix.AutoPackets.h;*.AutoPackets.xml,AutoPackets_Inline.jinja,$path/$fileprefix.AutoPackets.inl;*.AutoPackets.xml,AutoPackets_Source.jinja,$path/$fileprefix.AutoPackets.cpp"
)

# AzFramework
set(AZFRAMEWORK_DIR "${O3DE_ROOT}/Code/Framework/AzFramework")
set(azframework_lists
  "${AZFRAMEWORK_DIR}/AzFramework/azframework_files.cmake"
  "${AZFRAMEWORK_DIR}/Platform/${PAL}/platform_${pal}_files.cmake"
)
if(O3DE_WITH_XCB)
  list(APPEND azframework_lists "${AZFRAMEWORK_DIR}/Platform/Common/Xcb/azframework_xcb_files.cmake")
endif()
o3de_read_files(azframework_sources ${azframework_lists})
add_library(AzFramework ${azframework_sources})
target_compile_definitions(AzFramework PRIVATE AZF_EXPORTS)
target_include_directories(AzFramework
  PUBLIC
    "$<BUILD_INTERFACE:${AZFRAMEWORK_DIR};${AZFRAMEWORK_DIR}/Platform/${PAL}>"
    "$<INSTALL_INTERFACE:include/O3DE>"
  PRIVATE
    "${AZFRAMEWORK_DIR}/Platform/Common"
)
target_link_libraries(AzFramework
  PUBLIC AzCore AzNetworking ${ZSTD_TARGET} ${LZ4_TARGET}
  PRIVATE o3de_private
)
if(O3DE_WITH_XCB)
  target_compile_definitions(AzFramework PUBLIC PAL_TRAIT_LINUX_WINDOW_MANAGER_XCB)
  target_include_directories(AzFramework PUBLIC "$<BUILD_INTERFACE:${AZFRAMEWORK_DIR}/Platform/Common/Xcb>")
  # Public: the installed Xcb headers include xcb and xkbcommon headers.
  target_link_libraries(AzFramework PUBLIC
    xorg::xcb xorg::xcb-xkb xorg::xcb-xfixes xorg::xcb-randr xorg::xcb-keysyms
    xkbcommon::libxkbcommon xkbcommon::libxkbcommon-x11 PkgConfig::XCB_XINPUT
  )
else()
  # Upstream's "wayland" window manager: no native window or input implementation.
  target_compile_definitions(AzFramework PUBLIC PAL_TRAIT_LINUX_WINDOW_MANAGER_WAYLAND)
endif()

o3de_read_files(azframework_nativeui_sources
  "${AZFRAMEWORK_DIR}/AzFramework/azframework_nativeui_files.cmake"
  "${AZFRAMEWORK_DIR}/Platform/${PAL}/platform_nativeui_${pal}_files.cmake"
)
add_library(AzFrameworkNativeUI ${azframework_nativeui_sources})
set_target_properties(AzFrameworkNativeUI PROPERTIES OUTPUT_NAME "AzFramework.NativeUI")
target_compile_definitions(AzFrameworkNativeUI PRIVATE AZF_EXPORTS)
target_include_directories(AzFrameworkNativeUI PRIVATE "${AZFRAMEWORK_DIR}/Platform/Common")
target_link_libraries(AzFrameworkNativeUI PUBLIC AzFramework PRIVATE o3de_private)

# Install: headers keep upstream's include roots: each library folder, plus the
# Platform/<PAL> and Platform/Common folders as siblings, since platform headers include
# <../Common/...> and "../../../Common/...". The roots of the three libraries are merged.
set(O3DE_INCLUDE_DIR include/O3DE)
foreach(dir
    "${AZCORE_DIR}/AzCore" "${AZNETWORKING_DIR}/AzNetworking" "${AZFRAMEWORK_DIR}/AzFramework")
  cmake_path(GET dir FILENAME name)
  install(DIRECTORY "${dir}/" DESTINATION "${O3DE_INCLUDE_DIR}/${name}"
          FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp" PATTERN "*.inl")
endforeach()
foreach(dir "${AZCORE_DIR}" "${AZNETWORKING_DIR}" "${AZFRAMEWORK_DIR}")
  foreach(platform ${PAL} Common)
    install(DIRECTORY "${dir}/Platform/${platform}/" DESTINATION "${O3DE_INCLUDE_DIR}/Platform/${platform}"
            FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp" PATTERN "*.inl")
  endforeach()
endforeach()
install(DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/Azcg/Generated/AzNetworking/" DESTINATION "${O3DE_INCLUDE_DIR}"
        FILES_MATCHING PATTERN "*.h" PATTERN "*.inl")
install(DIRECTORY "${O3DE_LUA_SHIM_DIR}/" "${O3DE_RAPIDXML_INCLUDE_DIR}/" DESTINATION "${O3DE_INCLUDE_DIR}"
        FILES_MATCHING PATTERN "*.h")
install(TARGETS AzCore AzNetworking AzFramework AzFrameworkNativeUI
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
