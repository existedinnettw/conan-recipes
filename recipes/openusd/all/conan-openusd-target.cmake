# OpenUSD's static monolithic archive contains translation units whose only purpose
# is runtime type and plugin registration. They must not be discarded by the linker.
get_filename_component(_openusd_package_root "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
set(_openusd_archive
    "${_openusd_package_root}/lib/${CMAKE_STATIC_LIBRARY_PREFIX}usd_m${CMAKE_STATIC_LIBRARY_SUFFIX}")
# Replace CMakeDeps' ordinary archive target while retaining its platform and
# Conan dependency libraries through the generated dependency target.
set_property(TARGET OpenUSD::OpenUSD PROPERTY INTERFACE_LINK_LIBRARIES
    "$<LINK_LIBRARY:WHOLE_ARCHIVE,${_openusd_archive}>" openusd_DEPS_TARGET)
unset(_openusd_archive)
unset(_openusd_package_root)
