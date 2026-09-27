#include <cstdlib>
#include <iostream>

#include <Foo>
#include "testpkg_version.h"

int main() {
    std::cout << "testpkg " << TESTPKG_VERSION_STRING << ", foo() = " << foo() << "\n";
    return foo() == 42 ? EXIT_SUCCESS : EXIT_FAILURE;
}
