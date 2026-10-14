#include <chrono/physics/ChBodyEasy.h>
#include <chrono/physics/ChSystemNSC.h>

#include <iostream>

int main() {
    chrono::ChSystemNSC system;
    system.SetGravitationalAcceleration(chrono::ChVector3d(0, -9.81, 0));
    auto body = chrono_types::make_shared<chrono::ChBodyEasySphere>(0.5, 1000.0);
    system.Add(body);
    system.DoStepDynamics(0.01);
    std::cout << "Chrono body y after one step: " << body->GetPos().y() << std::endl;
    return 0;
}
