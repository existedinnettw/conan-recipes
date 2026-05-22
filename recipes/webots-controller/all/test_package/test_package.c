#include <webots/robot.h>

int main(void) {
  double (*c_symbol)(void) = &wb_robot_get_time;
  (void)c_symbol;
  return 0;
}
