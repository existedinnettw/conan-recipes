#include <mavconn/interface.hpp>

#include <algorithm>
#include <string>

int main()
{
  const auto dialects = mavconn::MAVConnInterface::get_known_dialects();
  return std::find(dialects.begin(), dialects.end(), std::string{"common"}) == dialects.end();
}
