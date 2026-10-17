# Injected with CMAKE_PROJECT_INCLUDE. Upstream's cmake/*.cmake modules (SAPIEN and
# sapien-vulkan-2) FetchContent every dependency; the recipe empties them and this file
# defines the targets they used to create, from the Conan packages instead.
include_guard(GLOBAL)

find_package(Eigen3 REQUIRED CONFIG)
find_package(PhysX REQUIRED CONFIG)
find_package(spdlog REQUIRED CONFIG)
find_package(assimp REQUIRED CONFIG)
find_package(VulkanHeaders REQUIRED CONFIG)
find_package(glm REQUIRED CONFIG)
find_package(glfw3 REQUIRED CONFIG)
find_package(Ktx REQUIRED CONFIG)
find_package(glslang REQUIRED CONFIG)
find_package(spirv-cross REQUIRED CONFIG)
find_package(OpenEXR REQUIRED CONFIG)
find_package(openvr REQUIRED CONFIG)
find_package(Threads REQUIRED)

add_library(eigen INTERFACE)
target_link_libraries(eigen INTERFACE Eigen3::Eigen)

add_library(physx5 INTERFACE)
target_link_libraries(physx5 INTERFACE PhysX::PhysX PhysX::PhysXCooking PhysX::PhysXExtensions
                                       PhysX::PhysXCharacterKinematic PhysX::PhysXVehicle)
target_compile_definitions(physx5 INTERFACE PHYSX_VERSION="${PhysX_VERSION}")

if(NOT TARGET glm)
    add_library(glm INTERFACE)
    target_link_libraries(glm INTERFACE glm::glm-header-only)
endif()

add_library(ktx INTERFACE)
target_link_libraries(ktx INTERFACE KTX::ktx)

add_library(glslang INTERFACE)
target_link_libraries(glslang INTERFACE glslang::glslang)
add_library(SPIRV INTERFACE)
target_link_libraries(SPIRV INTERFACE glslang::SPIRV)
# Sources include <SPIRV/GlslangToSpv.h>; glslang 15+ only installs <glslang/SPIRV/...>.
list(TRANSFORM glslang_INCLUDE_DIRS APPEND "/glslang" OUTPUT_VARIABLE _glslang_spirv_include)
target_include_directories(SPIRV INTERFACE ${_glslang_spirv_include})

add_library(OpenEXR INTERFACE)
target_link_libraries(OpenEXR INTERFACE OpenEXR::OpenEXR)

add_library(openvr_api INTERFACE)
target_link_libraries(openvr_api INTERFACE openvr::openvr)

set_property(TARGET glfw APPEND PROPERTY INTERFACE_COMPILE_DEFINITIONS GLFW_INCLUDE_VULKAN)

# imgui, ImGuizmo and ImGuiFileDialog stay vendored at the versions sapien-vulkan-2 pins
# (imgui 1.89.7 WIP): its Vulkan backend calls predate the API of Conan Center's imgui.
set(_imgui_dir "${SAPIEN_IMGUI_SOURCE_DIR}/imgui")
set(_imguizmo_dir "${SAPIEN_IMGUI_SOURCE_DIR}/imguizmo")
set(_imguifiledialog_dir "${SAPIEN_IMGUI_SOURCE_DIR}/imguifiledialog")
add_library(imgui STATIC
    ${_imgui_dir}/imgui.cpp
    ${_imgui_dir}/imgui_demo.cpp
    ${_imgui_dir}/imgui_draw.cpp
    ${_imgui_dir}/imgui_tables.cpp
    ${_imgui_dir}/imgui_widgets.cpp
    ${_imgui_dir}/backends/imgui_impl_glfw.cpp
    ${_imgui_dir}/backends/imgui_impl_vulkan.cpp
    ${_imguizmo_dir}/ImGuizmo.cpp
    ${_imguifiledialog_dir}/ImGuiFileDialog.cpp
)
target_link_libraries(imgui PUBLIC glfw Vulkan::Headers)
target_include_directories(imgui PUBLIC ${_imgui_dir} ${_imgui_dir}/backends ${_imguizmo_dir} ${_imguifiledialog_dir})
set_target_properties(imgui PROPERTIES POSITION_INDEPENDENT_CODE TRUE)
target_compile_definitions(imgui PUBLIC IMGUI_DEFINE_MATH_OPERATORS)
