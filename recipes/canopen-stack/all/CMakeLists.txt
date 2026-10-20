cmake_minimum_required(VERSION 3.15)
project(canopen-stack LANGUAGES C)

# Upstream src/CMakeLists.txt defines the canopen-stack target but has no
# install rules, and the top-level project also builds examples and tests.
# Reuse the upstream target definition and add the install rules here.

set(CANOPEN_STACK_UPSTREAM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

add_subdirectory("${CANOPEN_STACK_UPSTREAM_DIR}/src" canopen-stack)

# co_cfg.h only provides defaults (#ifndef), and these values size the public
# structs in co_core.h, so consumers must see the same values.
target_compile_definitions(canopen-stack PUBLIC
  CO_SSDO_N=${CO_SSDO_N}
  CO_CSDO_N=${CO_CSDO_N}
  CO_EMCY_N=${CO_EMCY_N}
  CO_RPDO_N=${CO_RPDO_N}
  CO_TPDO_N=${CO_TPDO_N}
  USE_LSS=${USE_LSS}
  USE_CSDO=${USE_CSDO}
)

include(GNUInstallDirs)
install(TARGETS canopen-stack
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
foreach(dir config core hal object/basic object/cia301 service/cia301 service/cia305)
  install(DIRECTORY "${CANOPEN_STACK_UPSTREAM_DIR}/src/${dir}/"
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/canopen-stack
    FILES_MATCHING PATTERN "*.h"
  )
endforeach()
