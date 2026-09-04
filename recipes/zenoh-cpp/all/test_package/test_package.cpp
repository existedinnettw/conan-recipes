#include <zenoh.hxx>

#include <iostream>

int main()
{
    zenoh::KeyExpr key("conan/test");
    std::cout << key.as_string_view() << '\n';
    return key.as_string_view() == "conan/test" ? 0 : 1;
}
