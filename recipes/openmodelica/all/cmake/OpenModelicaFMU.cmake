# Build-time FMU export with the OpenModelica compiler shipped in this package.
#
#   openmodelica_add_fmu(<target>
#     MODEL <Qualified.Class.Name>
#     [SOURCES <file.mo|package.mo>...]      files loaded with loadFile()
#     [LIBRARIES <Name[:version]>...]        libraries loaded with loadModel(), e.g. Modelica:4.1.0
#     [FMI_VERSION 2.0|3.0]                  default 2.0
#     [FMU_TYPE me|cs|me_cs]                 default me_cs
#     [NAME <fileNamePrefix>]                default <target>
#     [OUTPUT_DIRECTORY <dir>]               default ${CMAKE_CURRENT_BINARY_DIR}
#     [MODELICAPATH <dir>...]                library directories, searched before the ones in
#                                            the OPENMODELICALIBRARY environment variable
#     [OMC_FLAGS <flag>...])                 passed to setCommandLineOptions()
#
# Creates the custom target <target>, which builds <OUTPUT_DIRECTORY>/<NAME>.fmu, and sets
# the target property FMU_FILE (and the variable <target>_FMU_FILE) to that path.

include_guard(GLOBAL)

find_program(OPENMODELICA_OMC omc
             HINTS "${CMAKE_CURRENT_LIST_DIR}/../../../bin"
             NO_DEFAULT_PATH)
if(NOT OPENMODELICA_OMC)
  message(FATAL_ERROR "omc was not found next to ${CMAKE_CURRENT_LIST_FILE}")
endif()

function(_openmodelica_mos_string out value)
  string(REPLACE "\\" "\\\\" value "${value}")
  string(REPLACE "\"" "\\\"" value "${value}")
  set(${out} "\"${value}\"" PARENT_SCOPE)
endfunction()

function(openmodelica_add_fmu target)
  cmake_parse_arguments(PARSE_ARGV 1 arg
                        ""
                        "MODEL;FMI_VERSION;FMU_TYPE;NAME;OUTPUT_DIRECTORY"
                        "SOURCES;LIBRARIES;OMC_FLAGS;MODELICAPATH")
  if(arg_UNPARSED_ARGUMENTS)
    message(FATAL_ERROR "openmodelica_add_fmu: unknown arguments ${arg_UNPARSED_ARGUMENTS}")
  endif()
  if(NOT arg_MODEL)
    message(FATAL_ERROR "openmodelica_add_fmu: MODEL is required")
  endif()
  if(NOT arg_FMI_VERSION)
    set(arg_FMI_VERSION "2.0")
  endif()
  if(NOT arg_FMU_TYPE)
    set(arg_FMU_TYPE "me_cs")
  endif()
  if(NOT arg_NAME)
    set(arg_NAME "${target}")
  endif()
  if(NOT arg_OUTPUT_DIRECTORY)
    set(arg_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}")
  endif()

  # omc leaves its generated sources in the working directory, so give each FMU its own.
  set(work_dir "${CMAKE_CURRENT_BINARY_DIR}/${target}.omc")
  set(script "${work_dir}/${target}.mos")
  set(fmu "${arg_OUTPUT_DIRECTORY}/${arg_NAME}.fmu")

  # omc returns 0 even when a script statement fails, so every step checks its result
  # and exits non-zero itself.
  set(mos "")
  if(arg_OMC_FLAGS)
    list(JOIN arg_OMC_FLAGS " " flags)
    _openmodelica_mos_string(flags "${flags}")
    string(APPEND mos "if not setCommandLineOptions(${flags}) then print(getErrorString()); exit(1); end if;\n")
  endif()
  foreach(lib IN LISTS arg_LIBRARIES)
    string(REPLACE ":" ";" lib_parts "${lib}")
    list(GET lib_parts 0 lib_name)
    list(LENGTH lib_parts n)
    if(n GREATER 1)
      list(GET lib_parts 1 lib_version)
      _openmodelica_mos_string(lib_version "${lib_version}")
      string(APPEND mos "if not loadModel(${lib_name}, {${lib_version}}) then print(getErrorString()); exit(1); end if;\n")
    else()
      string(APPEND mos "if not loadModel(${lib_name}) then print(getErrorString()); exit(1); end if;\n")
    endif()
  endforeach()
  set(depends "")
  foreach(src IN LISTS arg_SOURCES)
    get_filename_component(src "${src}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
    list(APPEND depends "${src}")
    _openmodelica_mos_string(src_str "${src}")
    string(APPEND mos "if not loadFile(${src_str}) then print(getErrorString()); exit(1); end if;\n")
  endforeach()
  _openmodelica_mos_string(version_str "${arg_FMI_VERSION}")
  _openmodelica_mos_string(type_str "${arg_FMU_TYPE}")
  _openmodelica_mos_string(name_str "${arg_NAME}")
  string(APPEND mos
    "fmu := buildModelFMU(${arg_MODEL}, version=${version_str}, fmuType=${type_str}, fileNamePrefix=${name_str});\n"
    "if fmu == \"\" then print(getErrorString()); exit(1); end if;\n"
    "print(getErrorString());\n")
  file(GENERATE OUTPUT "${script}" CONTENT "${mos}")

  # The FMU's C sources are configured and compiled with the "cmake" found on PATH and the
  # compiler in CC, so hand omc the ones of this build.
  get_filename_component(cmake_dir "${CMAKE_COMMAND}" DIRECTORY)
  # Without OPENMODELICALIBRARY omc only searches ~/.openmodelica/libraries. The
  # modelica-standard-library package sets it in the Conan build environment; it is read
  # here, at configure time, so building later does not need that environment.
  set(modelicapath ${arg_MODELICAPATH})
  if(DEFINED ENV{OPENMODELICALIBRARY})
    string(REPLACE ":" ";" env_modelicapath "$ENV{OPENMODELICALIBRARY}")
    list(APPEND modelicapath ${env_modelicapath})
  endif()
  set(omc_env "PATH=${cmake_dir}:$ENV{PATH}" "CC=${CMAKE_C_COMPILER}")
  if(modelicapath)
    list(JOIN modelicapath ":" modelicapath)
    list(APPEND omc_env "OPENMODELICALIBRARY=${modelicapath}")
  endif()
  add_custom_command(
    OUTPUT "${fmu}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${work_dir}" "${arg_OUTPUT_DIRECTORY}"
    COMMAND "${CMAKE_COMMAND}" -E env ${omc_env} "${OPENMODELICA_OMC}" "${script}"
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different "${work_dir}/${arg_NAME}.fmu" "${fmu}"
    WORKING_DIRECTORY "${work_dir}"
    DEPENDS ${depends} "${script}"
    COMMENT "Exporting ${arg_MODEL} to ${arg_NAME}.fmu (FMI ${arg_FMI_VERSION} ${arg_FMU_TYPE})"
    VERBATIM)
  add_custom_target(${target} ALL DEPENDS "${fmu}")
  set_target_properties(${target} PROPERTIES FMU_FILE "${fmu}")
  set(${target}_FMU_FILE "${fmu}" PARENT_SCOPE)
endfunction()
