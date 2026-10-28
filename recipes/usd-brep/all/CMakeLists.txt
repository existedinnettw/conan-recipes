# Exported into the source tree; replaces upstream's premake build (repo_build + Packman), following the projects in
# premake5.lua and source/*/premake5.lua. Python bindings and tests are not built.
cmake_minimum_required(VERSION 3.20)
project(usd_brep LANGUAGES CXX)

option(USD_BREP_WITH_USD "Build the USD libraries" ON)
option(USD_BREP_WITH_HYDRA "Build the hdUsdBrep Hydra plugin" OFF)
option(USD_BREP_WITH_TOOLS "Build the command-line tools" ON)

include(GNUInstallDirs)

set(SRC "${CMAKE_CURRENT_SOURCE_DIR}")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(TBB CONFIG REQUIRED)
if(USD_BREP_WITH_USD)
  find_package(openusd CONFIG REQUIRED)
endif()

# Workspace-wide settings from premake5.lua, without FatalCompileWarnings.
add_compile_definitions(
  NOMINMAX
  SM_GRAPHICS_CALLBACKS=1
  $<$<CONFIG:Debug>:_DEBUG>
  $<$<CONFIG:Debug>:SM_DEBUG_CODE=1>
  $<$<CONFIG:Debug>:SM_GFX_CODE=1>
)
if(MSVC)
  add_compile_options(/utf-8 /bigobj /wd4244 /wd4305 /wd4267 /wd4251 -D_SCL_SECURE_NO_WARNINGS)
  add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
else()
  # Same rounding on every architecture (upstream sets it for aarch64, where GCC fuses FMAs).
  add_compile_options(-ffp-contract=off -Wno-deprecated)
endif()

function(usd_brep_library name kind)
  file(GLOB sources CONFIGURE_DEPENDS "${SRC}/source/${name}/src/*.cpp")
  list(FILTER sources EXCLUDE REGEX "/StdAfx\\.cpp$")
  add_library(${name} ${kind} ${sources})
  target_include_directories(${name} PUBLIC
    $<BUILD_INTERFACE:${SRC}/source/${name}/inc>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/usd-brep/${name}>)
  install(TARGETS ${name}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
  install(DIRECTORY "${SRC}/source/${name}/inc/"
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/usd-brep/${name}
    FILES_MATCHING PATTERN "*.h")
endfunction()

# Kernel
usd_brep_library(SMLib SHARED)
target_link_libraries(SMLib PUBLIC TBB::tbb TBB::tbbmalloc)
if(MSVC)
  target_compile_definitions(SMLib PRIVATE NL_DEBUG_CODE)
endif()

usd_brep_library(SM_API SHARED)
target_compile_definitions(SM_API PRIVATE SM_API_EXPORTS)
target_link_libraries(SM_API PUBLIC SMLib)

if(USD_BREP_WITH_USD)
  set(USD_BREP_USD_LIBS
    openusd::ar openusd::arch openusd::gf openusd::js openusd::kind openusd::pcp
    openusd::plug openusd::sdf openusd::sdr openusd::tf openusd::trace openusd::usd
    openusd::usdGeom openusd::usdLux openusd::usdShade openusd::usdUtils openusd::usdVol
    openusd::vt openusd::work)

  usd_brep_library(BREP_USD_DATA SHARED)
  target_compile_definitions(BREP_USD_DATA PRIVATE USDBREP_ENABLE_EXPORTS)
  target_link_libraries(BREP_USD_DATA PUBLIC ${USD_BREP_USD_LIBS})

  usd_brep_library(USD_BREP_UTILS SHARED)
  target_compile_definitions(USD_BREP_UTILS PRIVATE USD_BREP_ENABLE_EXPORTS)
  target_link_libraries(USD_BREP_UTILS PUBLIC BREP_USD_DATA)

  usd_brep_library(BREP_STAGING STATIC)
  target_link_libraries(BREP_STAGING PUBLIC BREP_USD_DATA)

  usd_brep_library(OCCT_BREP_IMPORT STATIC)
  target_link_libraries(OCCT_BREP_IMPORT PUBLIC BREP_STAGING)

  # Uses the importer's record structs (header-only here).
  usd_brep_library(OCCT_BREP_EXPORT STATIC)
  target_include_directories(OCCT_BREP_EXPORT PUBLIC $<BUILD_INTERFACE:${SRC}/source/OCCT_BREP_IMPORT/inc>)
  target_link_libraries(OCCT_BREP_EXPORT PUBLIC USD_BREP_UTILS)

  usd_brep_library(BREP_SM_USD SHARED)
  target_compile_definitions(BREP_SM_USD PRIVATE SMU_ENABLE_EXPORTS)
  target_link_libraries(BREP_SM_USD PUBLIC SMLib BREP_USD_DATA)

  usd_brep_library(SM_API_USD SHARED)
  target_compile_definitions(SM_API_USD PRIVATE SM_API_USD_EXPORTS)
  target_link_libraries(SM_API_USD PUBLIC SM_API BREP_SM_USD)

  if(USD_BREP_WITH_HYDRA)
    usd_brep_library(HYDRA_USD_BREP SHARED)
    target_compile_definitions(HYDRA_USD_BREP PRIVATE HDUSDBREP_EXPORTS)
    target_link_libraries(HYDRA_USD_BREP PUBLIC SM_API_USD
      openusd::hd openusd::hdGp openusd::usdImaging openusd::hf openusd::pxOsd)
  endif()

  if(USD_BREP_WITH_TOOLS)
    function(usd_brep_tool name)
      add_executable(${name} ${ARGN})
      install(TARGETS ${name} RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
    endfunction()
    usd_brep_tool(occt_to_usd "${SRC}/tools/occt_to_usd/occt_to_usd.cpp")
    target_link_libraries(occt_to_usd PRIVATE OCCT_BREP_IMPORT)
    usd_brep_tool(occt_dump "${SRC}/tools/occt_to_usd/occt_dump.cpp")
    target_link_libraries(occt_dump PRIVATE OCCT_BREP_IMPORT)
    usd_brep_tool(usd_to_occt "${SRC}/tools/usd_to_occt/usd_to_occt.cpp")
    target_link_libraries(usd_to_occt PRIVATE OCCT_BREP_EXPORT)
    file(GLOB smtess_sources "${SRC}/tools/smtess_usd/src/*.cpp")
    usd_brep_tool(smtess_usd ${smtess_sources})
    target_link_libraries(smtess_usd PRIVATE BREP_SM_USD)
    file(GLOB validator_sources "${SRC}/tools/brep_geometry_validator/src/*.cpp")
    usd_brep_tool(brep_geometry_validator ${validator_sources})
    target_link_libraries(brep_geometry_validator PRIVATE SM_API_USD)
  endif()
endif()
