# Library build for aruco2: upstream's CMakeLists only builds the utilities, each compiling the
# library sources in. This builds the library itself (no utilities).
cmake_minimum_required(VERSION 3.15)
project(aruco2 LANGUAGES CXX)

find_package(OpenCV REQUIRED CONFIG)

set(SRC ${ARUCO2_SOURCE_DIR})
# OpenCL kernels as C++ strings (upstream's generator).
add_custom_command(
    OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/opencl_kernels_aruco2.hpp" "${CMAKE_CURRENT_BINARY_DIR}/opencl_kernels_aruco2.cpp"
    COMMAND ${CMAKE_COMMAND} "-DCL_PATH=${SRC}/opencl/aruco2detect.cl"
            "-DHPP_PATH=${CMAKE_CURRENT_BINARY_DIR}/opencl_kernels_aruco2.hpp"
            "-DCPP_PATH=${CMAKE_CURRENT_BINARY_DIR}/opencl_kernels_aruco2.cpp"
            -P "${SRC}/utils/cl2cpp.cmake"
    DEPENDS "${SRC}/opencl/aruco2detect.cl" "${SRC}/utils/cl2cpp.cmake"
    VERBATIM)

add_library(aruco2
    ${SRC}/src/aruco2.cpp ${SRC}/src/aruco_dictionary.cpp ${SRC}/src/aruco2_fractal.cpp
    "${CMAKE_CURRENT_BINARY_DIR}/opencl_kernels_aruco2.cpp")
target_compile_features(aruco2 PUBLIC cxx_std_17)
target_include_directories(aruco2
    PUBLIC $<BUILD_INTERFACE:${SRC}> $<INSTALL_INTERFACE:include>
    PRIVATE ${SRC}/src ${SRC}/opencv2/objdetect ${CMAKE_CURRENT_BINARY_DIR})
target_link_libraries(aruco2 PUBLIC opencv_core opencv_imgproc PRIVATE opencv_flann opencv_calib3d)

install(TARGETS aruco2 RUNTIME DESTINATION bin LIBRARY DESTINATION lib ARCHIVE DESTINATION lib)
install(FILES ${SRC}/opencv2/objdetect/aruco2.hpp DESTINATION include/opencv2/objdetect)
