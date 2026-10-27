cmake_minimum_required(VERSION 3.15)
project(rsmotion LANGUAGES CXX)

include(GNUInstallDirs)

add_library(rsmotion src/library/src/rsmotion.cpp)
target_compile_features(rsmotion PUBLIC cxx_std_14)
target_include_directories(rsmotion
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src/library/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_compile_options(rsmotion PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-fpermissive>
)
install(TARGETS rsmotion
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(DIRECTORY src/library/include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
