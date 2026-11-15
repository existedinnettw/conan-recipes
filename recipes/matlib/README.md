# MatLib

Header-only Tellicious/MatLib pinned to commit
`4300e9c761ef2bc63c5816b71204434cf76f9aa0` (2023-12-09), as
`matlib/cci.20231209`. Requires C++11 or newer.

Use `find_package(matlib CONFIG REQUIRED)` and link `matlib::matlib`, then
include `<MatLib.h>`. The recipe adds missing standard includes and removes
template arguments from constructor/destructor declarations for C++20 compatibility.
