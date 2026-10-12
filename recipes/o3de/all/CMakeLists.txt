# Builds O3DE libraries from the engine source tree, replacing O3DE's own build system, which
# needs the whole engine, a downloaded Python and its prebuilt 3rdParty packages.
# The core framework libraries (AzCore, AzNetworking, AzFramework) are described here; their
# source and compile settings mirror Code/Framework/*/CMakeLists.txt and
# cmake/Platform/{Common,Linux}/Configurations_*.cmake. The other engine libraries and the Gems
# use their own CMakeLists.txt, through o3de_compat.cmake.
cmake_minimum_required(VERSION 3.22)
project(O3DE LANGUAGES C CXX)

set(O3DE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/o3de")
set(O3DE_RAPIDXML_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/rapidxml/RapidXML/include")
set(O3DE_CONFIGURATION "profile" CACHE STRING "O3DE build configuration: debug, profile or release")
set(O3DE_PYTHONPATH "" CACHE STRING "Python path holding jinja2 for cmake/AzAutoGen.py")
option(O3DE_WITH_XCB "Linux: native windows and keyboard/mouse input through XCB" ON)
option(O3DE_WITH_EDITOR "Editor libraries (AzQtComponents, AzToolsFramework) and the Gems' editor and builder libraries" OFF)
set(O3DE_GEMS "" CACHE STRING "Gems to build (;-separated); the Gems they depend on are added")
option(O3DE_WITH_ASSET_PROCESSOR "AssetProcessor, AssetProcessorBatch and AssetBuilder, and the engine data they run with (needs O3DE_WITH_EDITOR and shared libraries)" OFF)
option(O3DE_WITH_LAUNCHER "The generic game launcher (O3DE.GameLauncher, runs a project's processed assets), and the engine data it runs with (needs shared libraries)" OFF)
set(O3DE_EXECUTABLES)
if(O3DE_WITH_ASSET_PROCESSOR)
  list(APPEND O3DE_EXECUTABLES AssetProcessor AssetProcessorBatch AssetBuilder)
endif()
if(O3DE_WITH_LAUNCHER)
  list(APPEND O3DE_EXECUTABLES O3DE.GameLauncher)
endif()
if(O3DE_EXECUTABLES)
  # The package is an engine root: executables and Gem modules in bin, the libraries in lib.
  set(O3DE_RUNTIME_FILES ON)
  set(CMAKE_INSTALL_RPATH "$ORIGIN/../lib;$ORIGIN")
endif()

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
  # Not among xorg/system's components (libxcb-xinput-dev on Debian/Ubuntu).
  find_path(XCB_XINPUT_INCLUDE_DIR xcb/xinput.h REQUIRED)
  find_library(XCB_XINPUT_LIBRARY xcb-xinput REQUIRED)
  add_library(xcb-xinput UNKNOWN IMPORTED)
  set_target_properties(xcb-xinput PROPERTIES
    IMPORTED_LOCATION "${XCB_XINPUT_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${XCB_XINPUT_INCLUDE_DIR}"
  )
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
# Hidden visibility, as upstream (Configurations_clang.cmake): in a shared build, Gem modules
# would otherwise share the inline symbols (e.g. component descriptors' vtables) of the first module
# that defined them, and crash when that one is unloaded first. Not for shared libraries with GCC,
# which also hides the EBus template instantiations AzCore exports (AZ_INSTANTIATE_EBUS_*), and
# AzFramework fails to link.
if(NOT BUILD_SHARED_LIBS OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
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
  # o3de_compat.cmake's targets only list the C/C++ files as sources.
  get_target_property(all_files ${target} O3DE_ALLFILES)
  if(NOT all_files)
    get_target_property(all_files ${target} SOURCES)
  endif()
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
o3de_read_files(azframework_sources
  "${AZFRAMEWORK_DIR}/AzFramework/azframework_files.cmake"
  "${AZFRAMEWORK_DIR}/Platform/${PAL}/platform_${pal}_files.cmake"
)
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
else()
  # Upstream's "wayland" window manager: no native window or input implementation.
  target_compile_definitions(AzFramework PUBLIC PAL_TRAIT_LINUX_WINDOW_MANAGER_WAYLAND)
endif()

# The native windows and input (XCB) are in AzFramework.NativeUI, as upstream
# (Platform/Linux/platform_nativeui_linux.cmake).
set(azframework_nativeui_lists
  "${AZFRAMEWORK_DIR}/AzFramework/azframework_nativeui_files.cmake"
  "${AZFRAMEWORK_DIR}/Platform/${PAL}/platform_nativeui_${pal}_files.cmake"
)
if(O3DE_WITH_XCB)
  list(APPEND azframework_nativeui_lists "${AZFRAMEWORK_DIR}/Platform/Common/Xcb/azframework_xcb_files.cmake")
endif()
o3de_read_files(azframework_nativeui_sources ${azframework_nativeui_lists})
add_library(AzFrameworkNativeUI ${azframework_nativeui_sources})
set_target_properties(AzFrameworkNativeUI PROPERTIES OUTPUT_NAME "AzFramework.NativeUI")
target_compile_definitions(AzFrameworkNativeUI PRIVATE AZF_EXPORTS)
target_include_directories(AzFrameworkNativeUI PRIVATE "${AZFRAMEWORK_DIR}/Platform/Common")
target_link_libraries(AzFrameworkNativeUI PUBLIC AzFramework PRIVATE o3de_private)
if(O3DE_WITH_XCB)
  target_include_directories(AzFrameworkNativeUI PUBLIC "$<BUILD_INTERFACE:${AZFRAMEWORK_DIR}/Platform/Common/Xcb>")
  # Public: the installed Xcb headers include xcb and xkbcommon headers.
  target_link_libraries(AzFrameworkNativeUI PUBLIC
    xorg::xcb xorg::xcb-xkb xorg::xcb-xfixes xorg::xcb-randr xorg::xcb-keysyms
    xkbcommon::libxkbcommon xkbcommon::libxkbcommon-x11 xcb-xinput
  )
endif()

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

# Engine libraries and Gems built with their own CMakeLists.txt
add_library(AZ::AzCore ALIAS AzCore)
add_library(AZ::AzNetworking ALIAS AzNetworking)
add_library(AZ::AzFramework ALIAS AzFramework)
add_library(AZ::AzFramework.NativeUI ALIAS AzFrameworkNativeUI)
include(o3de_compat.cmake)
o3de_register_external(AzCore azcore)
o3de_register_external(AzNetworking aznetworking)
o3de_register_external(AzFramework azframework)
o3de_register_external(AzFrameworkNativeUI azframework-nativeui)

# 3rdParty packages, from Conan. Upstream's packages a target needs but which are not here
# (DXC, azslc, PhysX, ...) leave that target out.
o3de_add_3rdparty(RapidJSON TARGETS rapidjson REQUIRES rapidjson::rapidjson)
o3de_add_3rdparty(Lua TARGETS lua::lua REQUIRES lua::lua)
o3de_add_3rdparty(ZLIB TARGETS ZLIB::ZLIB REQUIRES zlib::zlib)
o3de_add_3rdparty(zstd TARGETS ${ZSTD_TARGET} REQUIRES zstd::zstd)
o3de_add_3rdparty(lz4 TARGETS ${LZ4_TARGET} REQUIRES lz4::lz4)
o3de_add_3rdparty(OpenSSL TARGETS openssl::openssl REQUIRES openssl::openssl)
foreach(package TIFF PNG Freetype meshoptimizer SQLite3 xxHash mcpp expat Qt5)
  find_package(${package} CONFIG QUIET)
endforeach()
if(TARGET TIFF::TIFF)
  o3de_add_3rdparty(TIFF TARGETS TIFF::TIFF REQUIRES libtiff::libtiff)
endif()
if(TARGET PNG::PNG)
  o3de_add_3rdparty(PNG TARGETS PNG::PNG REQUIRES libpng::libpng)
endif()
if(TARGET Freetype::Freetype)
  o3de_add_3rdparty(Freetype TARGETS Freetype::Freetype REQUIRES freetype::freetype)
endif()
if(TARGET meshoptimizer::meshoptimizer)
  o3de_add_3rdparty(meshoptimizer TARGETS meshoptimizer::meshoptimizer REQUIRES meshoptimizer::meshoptimizer)
endif()
if(TARGET xxHash::xxhash)
  # Upstream's package puts xxhash.h in an xxhash/ folder.
  set(O3DE_XXHASH_SHIM_DIR "${CMAKE_CURRENT_BINARY_DIR}/xxhash-shim")
  file(WRITE "${O3DE_XXHASH_SHIM_DIR}/xxhash/xxhash.h" "#pragma once\n#include <xxhash.h>\n")
  o3de_add_3rdparty(xxhash TARGETS xxHash::xxhash REQUIRES xxhash::xxhash INCLUDE_DIRECTORIES "${O3DE_XXHASH_SHIM_DIR}")
endif()
if(TARGET expat::expat)
  o3de_add_3rdparty(expat TARGETS expat::expat REQUIRES expat::expat)
endif()
if(TARGET mcpp::mcpp)
  o3de_add_3rdparty(mcpp TARGETS mcpp::mcpp REQUIRES mcpp::mcpp)
  # The shader builder's runtime dependencies (upstream copies them next to the executables):
  # the azslc and directx-shader-compiler packages are run requirements instead.
  o3de_add_3rdparty(azslc)
  o3de_add_3rdparty(DirectXShaderCompilerDxc)
  o3de_add_3rdparty(SPIRVCross)
endif()
if(TARGET SQLite::SQLite3)
  o3de_add_3rdparty(SQLite TARGETS SQLite::SQLite3 REQUIRES sqlite3::sqlite3)
endif()
if(O3DE_WITH_EDITOR)
  # AzQtComponents uses Qt's private headers, which upstream's Qt package exposes.
  foreach(module Core Gui Widgets Svg Xml Network Concurrent OpenGL Test)
    set(targets Qt5::${module})
    if(module MATCHES "^(Core|Gui|Widgets)$")
      list(APPEND targets Qt5::${module}Private)
    endif()
    o3de_add_3rdparty(Qt::${module} TARGETS ${targets} REQUIRES qt::qt${module})
  endforeach()
  add_library(3rdParty::Qt ALIAS 3rdParty::Qt::Core)
endif()

o3de_discover_gems("${O3DE_ROOT}")
# Vendored in the Atom_RHI_Vulkan Gem (its 3rdParty/Find*.cmake). The Vulkan RHI's Linux headers
# include XCB's: without XCB (headless), only the Null RHI is built.
set(vulkan_external "${O3DE_ROOT}/Gems/Atom/RHI/Vulkan/External")
if(O3DE_WITH_XCB)
  o3de_add_3rdparty(glad_vulkan INCLUDE_DIRECTORIES "${vulkan_external}/glad/2.0.0-beta/include"
                    COMPILE_DEFINITIONS VK_USE_PLATFORM_XCB_KHR TARGETS xorg::xcb REQUIRES xorg::xcb)
endif()
# Upstream's package only copies the Vulkan validation layer next to the binaries; the RHI
# enables validation when the layer is installed.
o3de_add_3rdparty(vulkan-validationlayers)
o3de_add_3rdparty(amd_vma INCLUDE_DIRECTORIES "${vulkan_external}/vma/3.1.0-009ecd1/include"
                  COMPILE_DEFINITIONS VMA_STATIC_VULKAN_FUNCTIONS=0 VMA_DYNAMIC_VULKAN_FUNCTIONS=0)
add_subdirectory("${O3DE_ROOT}/Code/Framework/AtomCore" "${CMAKE_BINARY_DIR}/o3de/Code/Framework/AtomCore")
add_subdirectory("${O3DE_ROOT}/Code/Legacy/CryCommon" "${CMAKE_BINARY_DIR}/o3de/Code/Legacy/CryCommon")
if(O3DE_WITH_EDITOR)
  # Not AZ_QT_COMPONENTS_STATIC when it is static: it includes a rcc_resources.h upstream does not
  # have; the export attributes it removes do no harm in a static library.
  add_subdirectory("${O3DE_ROOT}/Code/Framework/AzQtComponents" "${CMAKE_BINARY_DIR}/o3de/Code/Framework/AzQtComponents")
  # The libraries the Editor and the asset builders are made of, used by the Gems' editor and
  # builder libraries. Their executables are not built.
  if(O3DE_WITH_ASSET_PROCESSOR)
    # It adds AssetBuilderSDK and AssetBuilder.
    set(asset_processor_dir Code/Tools/AssetProcessor)
  else()
    set(asset_processor_dir Code/Tools/AssetProcessor/AssetBuilderSDK)
  endif()
  foreach(dir
      Code/Framework/AzToolsFramework Code/Editor ${asset_processor_dir}
      Code/Tools/SceneAPI/SceneCore Code/Tools/SceneAPI/SceneData Code/Tools/SceneAPI/SceneUI)
    add_subdirectory("${O3DE_ROOT}/${dir}" "${CMAKE_BINARY_DIR}/o3de/${dir}")
  endforeach()
  # AzToolsFrameworkAPI.h leaves it undefined in a monolithic build, which upstream does not
  # build the editor libraries for.
  if(NOT BUILD_SHARED_LIBS)
    target_compile_definitions(AzToolsFramework PRIVATE AZTF_API_EXPORT=)
  endif()
endif()
if(O3DE_WITH_LAUNCHER)
  # CrySystem is a module the launcher loads.
  foreach(dir Code/Framework/AzGameFramework Code/Legacy/CrySystem Code/Tools/RemoteConsole Code/LauncherUnified)
    add_subdirectory("${O3DE_ROOT}/${dir}" "${CMAKE_BINARY_DIR}/o3de/${dir}")
  endforeach()
  # Upstream's launchers load the Atom Gems' runtime modules through Atom_AtomBridge's runtime
  # dependencies, but AtomBridge needs Gems this recipe does not build: the ones of them that are built.
  set(O3DE_EXTRA_CLIENT_TARGETS
    Atom_RHI.Private Atom_RPI.Private Atom_RHI_Null.Private Atom_RHI_Vulkan.Private Atom_Feature_Common
    Atom_Bootstrap Atom_Component_DebugCamera AtomImGuiTools CommonFeaturesAtom ImguiAtom
  )
endif()
set(O3DE_REQUESTED_GEMS ${O3DE_GEMS})
o3de_add_gems(${O3DE_GEMS})
if(O3DE_WITH_ASSET_PROCESSOR)
  # Upstream's builders load the Atom Gems' runtime and editor modules (which reflect the asset
  # types, e.g. Atom_RPI.Editor for passes) through Atom_AtomBridge.Builders' runtime dependencies,
  # but AtomBridge needs Gems this recipe does not build: the ones of them that are built.
  # "A|B" stands for the first of them that is built: CommonFeaturesAtom.Editor needs
  # AtomToolsFramework (Python); its runtime module reflects the asset types too.
  set(O3DE_EXTRA_BUILDER_TARGETS
    Atom_RHI.Private Atom_RPI.Builders Atom_RPI.Editor Atom_RHI_Null.Private Atom_RHI_Null.Builders
    Atom_Feature_Common.Builders Atom_Feature_Common.Editor Atom_Bootstrap AtomShader.Builders
    Atom_Component_DebugCamera Atom_RHI_Vulkan.Private Atom_RHI_Vulkan.Builders
    "CommonFeaturesAtom.Editor|CommonFeaturesAtom" "ImguiAtom"
  )
endif()
o3de_finalize()

if(O3DE_RUNTIME_FILES)
  # The engine data the executables run with, at the package root (the engine root they find by
  # looking for engine.json above their folder): the engine's settings and assets, and the
  # selected Gems' manifests, settings and assets. engine.json lists only those Gems.
  get_property(selected_gems GLOBAL PROPERTY O3DE_SELECTED_GEMS)
  file(READ "${O3DE_ROOT}/engine.json" engine_json)
  set(subdirectories "[]")
  foreach(gem IN LISTS selected_gems)
    get_property(gem_root GLOBAL PROPERTY "@GEMROOT:${gem}@")
    file(RELATIVE_PATH rel "${O3DE_ROOT}" "${gem_root}")
    string(JSON n LENGTH "${subdirectories}")
    string(JSON subdirectories SET "${subdirectories}" ${n} "\"${rel}\"")
    install(FILES "${gem_root}/gem.json" DESTINATION "${rel}")
    foreach(data_dir Assets Registry)
      if(IS_DIRECTORY "${gem_root}/${data_dir}")
        install(DIRECTORY "${gem_root}/${data_dir}" DESTINATION "${rel}")
      endif()
    endforeach()
  endforeach()
  string(JSON engine_json SET "${engine_json}" external_subdirectories "${subdirectories}")
  foreach(key projects templates repos)
    string(JSON engine_json SET "${engine_json}" ${key} "[]")
  endforeach()
  file(WRITE "${CMAKE_BINARY_DIR}/engine.json" "${engine_json}\n")
  install(FILES "${CMAKE_BINARY_DIR}/engine.json" DESTINATION .)
  install(DIRECTORY "${O3DE_ROOT}/Registry" "${O3DE_ROOT}/Assets" DESTINATION .)
  # Atom_Feature_Common's SceneSrgAll.azsli includes the Terrain Gem's scene SRG partial, which shader
  # includes find under <engine root>/Gems whether Terrain is used or not.
  install(FILES "${O3DE_ROOT}/Gems/Terrain/Assets/Shaders/Terrain/SceneSrg.azsli"
          DESTINATION Gems/Terrain/Assets/Shaders/Terrain)
endif()
