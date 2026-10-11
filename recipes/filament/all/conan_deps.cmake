# Included right after project(TNT) through CMAKE_PROJECT_TNT_INCLUDE. Defines the targets of the
# third_party libraries the recipe takes from Conan instead (their add_subdirectory() calls are
# removed), under the names Filament links them by. INTERFACE targets are left out of Filament's
# combined static libraries (filamat, geometry), so consumers get these from Conan, not twice.

find_package(zstd REQUIRED CONFIG)
add_library(zstd INTERFACE)
if (TARGET zstd::libzstd_static)
    target_link_libraries(zstd INTERFACE zstd::libzstd_static)
else()
    target_link_libraries(zstd INTERFACE zstd::libzstd_shared)
endif()

find_package(draco REQUIRED CONFIG)
add_library(dracodec INTERFACE)
target_link_libraries(dracodec INTERFACE draco::draco)

find_package(meshoptimizer REQUIRED CONFIG)
add_library(meshoptimizer INTERFACE)
target_link_libraries(meshoptimizer INTERFACE meshoptimizer::meshoptimizer)

# Filament includes <mikktspace/mikktspace.h>; Conan's package has <mikktspace.h>.
find_package(mikktspace REQUIRED CONFIG)
set(_conan_shims "${CMAKE_BINARY_DIR}/conan_shims")
file(WRITE "${_conan_shims}/mikktspace/mikktspace.h" "#include <mikktspace.h>\n")
add_library(mikktspace INTERFACE)
target_include_directories(mikktspace INTERFACE "${_conan_shims}")
target_link_libraries(mikktspace INTERFACE mikktspace::mikktspace)

# Conan's cgltf is compiled with CGLTF_IMPLEMENTATION (removed from gltfio by the recipe).
find_package(cgltf REQUIRED CONFIG)
add_library(cgltf INTERFACE)
target_link_libraries(cgltf INTERFACE cgltf::cgltf)

find_package(jsmn REQUIRED CONFIG)
add_library(jsmn INTERFACE)
target_link_libraries(jsmn INTERFACE jsmn::jsmn)

find_package(tsl-robin-map REQUIRED CONFIG)
add_library(tsl INTERFACE)
target_link_libraries(tsl INTERFACE tsl::robin_map)

find_package(imgui REQUIRED CONFIG)
add_library(imgui INTERFACE)
target_link_libraries(imgui INTERFACE imgui::imgui)

# Upstream's stb target is its stb_image implementation (with some formats disabled), compiled
# here against Conan's header; the copy keeps "stb_image.h" from resolving next to the source.
find_package(stb REQUIRED CONFIG)
configure_file("${CMAKE_SOURCE_DIR}/third_party/stb/stb_image.cpp" "${_conan_shims}/stb_image.cpp" COPYONLY)
add_library(stb STATIC "${_conan_shims}/stb_image.cpp")
target_link_libraries(stb PUBLIC stb::stb)
install(TARGETS stb ARCHIVE DESTINATION lib)

if (FILAMENT_SUPPORTS_WEBP_TEXTURES)
    find_package(WebP REQUIRED CONFIG)
    add_library(webpdecoder INTERFACE)
    target_link_libraries(webpdecoder INTERFACE WebP::webpdecoder)
endif()

# Only the tools (imageio) use libpng and zlib.
find_package(PNG REQUIRED)
add_library(png INTERFACE)
target_link_libraries(png INTERFACE PNG::PNG)

find_package(ZLIB REQUIRED)
add_library(z INTERFACE)
target_link_libraries(z INTERFACE ZLIB::ZLIB)

# System headers of the backend's platforms (X11, GLX, EGL, Wayland), which upstream expects on the
# default include path. FILAMENT_CONAN_BACKEND_PACKAGES is a list of "<find_package name>=<target>".
foreach(_package_target IN LISTS FILAMENT_CONAN_BACKEND_PACKAGES)
    string(REPLACE "=" ";" _package_target "${_package_target}")
    list(GET _package_target 0 _package)
    list(GET _package_target 1 _target)
    find_package(${_package} REQUIRED CONFIG)
    list(APPEND _conan_backend_targets ${_target})
endforeach()
# PUBLIC: bluevk's vulkan.h includes the window system headers too, wherever it is included.
function(_conan_link_backend_packages)
    foreach(_target IN ITEMS backend bluegl bluevk)
        if (TARGET ${_target})
            # Equivalent to target_link_libraries(PUBLIC), which bluevk's plain-signature calls
            # do not allow.
            set_property(TARGET ${_target} APPEND PROPERTY LINK_LIBRARIES ${_conan_backend_targets})
            set_property(TARGET ${_target} APPEND PROPERTY INTERFACE_LINK_LIBRARIES ${_conan_backend_targets})
        endif()
    endforeach()
endfunction()
if (_conan_backend_targets)
    # backend and its OpenGL and Vulkan loaders are only defined later in the top-level CMakeLists.
    cmake_language(DEFER CALL _conan_link_backend_packages)
endif()
