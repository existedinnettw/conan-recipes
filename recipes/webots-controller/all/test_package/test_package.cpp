#include <webots/Robot.hpp>
#include <webots/robot.h>
#include <iostream>

int main() {
  auto cpp_symbol = &webots::Robot::getBasicTimeStep;
  auto c_symbol = &wb_robot_get_time;
  (void)cpp_symbol;
  (void)c_symbol;
  std::cout << "Success!" << std::endl;
  return 0;
}