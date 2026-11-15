cmake_minimum_required(VERSION 3.15)
project(vectorquaternionmatrix LANGUAGES CXX)

# Build the reusable library only; upstream main.cpp is a PlatformIO demo.
add_library(vectorquaternionmatrix src/src/VectorQuaternionMatrix.cpp)
target_compile_features(vectorquaternionmatrix PUBLIC cxx_std_20)
target_include_directories(vectorquaternionmatrix PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src/src>
    $<INSTALL_INTERFACE:include>
)
set_target_properties(vectorquaternionmatrix PROPERTIES WINDOWS_EXPORT_ALL_SYMBOLS ON)
include(GNUInstallDirs)
install(TARGETS vectorquaternionmatrix
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(DIRECTORY src/src/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR} FILES_MATCHING PATTERN "*.h")
