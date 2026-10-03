cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(Trilinos REQUIRED CONFIG)

foreach(_package Teuchos Epetra AztecOO Ifpack ML)
  if(NOT _package IN_LIST Trilinos_PACKAGE_LIST)
    message(FATAL_ERROR "${_package} missing from Trilinos_PACKAGE_LIST: ${Trilinos_PACKAGE_LIST}")
  endif()
endforeach()

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE Trilinos::all_libs)
target_compile_features(test_package PRIVATE cxx_std_17)
