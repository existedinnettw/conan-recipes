#include <mavsdk/mavsdk.h>

#include <iostream>

int main()
{
    mavsdk::Mavsdk sdk{mavsdk::Mavsdk::Configuration{
        mavsdk::ComponentType::GroundStation}};
    std::cout << sdk.version() << '\n';
    return sdk.version().empty() ? 1 : 0;
}
