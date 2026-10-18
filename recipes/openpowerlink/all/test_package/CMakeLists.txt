cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(openpowerlink REQUIRED CONFIG)

if(TARGET openpowerlink::oplkcn)
    set(OPLK_TARGET openpowerlink::oplkcn)
    set(OBJDICT CiA401_CN)
else()
    set(OPLK_TARGET openpowerlink::oplkmn)
    set(OBJDICT CiA302-4_MN)
endif()

add_executable(test_package test_package.c ${OPENPOWERLINK_OBDCREATE_SOURCES})
target_include_directories(test_package PRIVATE
    ${OPENPOWERLINK_APPS_COMMON_DIR}
    ${OPENPOWERLINK_OBJDICTS_DIR}/${OBJDICT}
)
if(OBJDICT STREQUAL "CiA302-4_MN")
    target_compile_definitions(test_package PRIVATE NMT_MAX_NODE_ID=254)
endif()
target_link_libraries(test_package PRIVATE ${OPLK_TARGET})
