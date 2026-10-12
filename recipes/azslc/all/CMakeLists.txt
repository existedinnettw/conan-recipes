# Upstream's src/CMakeLists.txt, with CLI11 and the ANTLR4 C++ runtime from Conan instead of
# FetchContent (upstream fetches O3DE's antlr4 branch o3de-4.13.2, which is ANTLR 4.13.2).
cmake_minimum_required(VERSION 3.20)
project(Azslc LANGUAGES CXX)

find_package(CLI11 REQUIRED CONFIG)
find_package(antlr4-runtime REQUIRED CONFIG)

set(AZSLC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src/src")

file(GLOB_RECURSE azslc_PlatformSRC
  "${AZSLC_DIR}/../Platform/*.cpp"
  "${AZSLC_DIR}/../Platform/*.h"
)
file(GLOB azslc_LocalSRC
  "${AZSLC_DIR}/*.cpp"
  "${AZSLC_DIR}/*.tpl"
  "${AZSLC_DIR}/*.h"
)
file(GLOB azslc_ExternalSRC
  "${AZSLC_DIR}/external/jsoncpp/dist/json/*.h"
  "${AZSLC_DIR}/external/jsoncpp/dist/*.cpp"
  "${AZSLC_DIR}/external/mpark-variant/master/*.hpp"
  "${AZSLC_DIR}/external/tiny/*.h"
)
file(GLOB azslc_GeneratedSrc "${AZSLC_DIR}/generated/*.cpp")

add_executable(azslc ${azslc_LocalSRC} ${azslc_PlatformSRC} ${azslc_GeneratedSrc} ${azslc_ExternalSRC})
target_compile_features(azslc PRIVATE cxx_std_17)
target_include_directories(azslc PRIVATE
  "${AZSLC_DIR}"
  "${AZSLC_DIR}/external"
  "${AZSLC_DIR}/../Platform/Common/src"
  "${AZSLC_DIR}/external/mpark-variant/master"
  "${AZSLC_DIR}/external/tiny"
)
if(MSVC)
  target_compile_options(azslc PRIVATE /permissive- /Zc:__cplusplus /utf-8)
  target_compile_definitions(azslc PRIVATE _CRT_SECURE_NO_WARNINGS _SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING)
endif()
if(TARGET antlr4_static)
  target_link_libraries(azslc PRIVATE antlr4_static)
else()
  target_link_libraries(azslc PRIVATE antlr4_shared)
endif()
target_link_libraries(azslc PRIVATE CLI11::CLI11)

install(TARGETS azslc RUNTIME DESTINATION bin)
