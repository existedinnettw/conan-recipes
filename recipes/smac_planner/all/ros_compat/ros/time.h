#ifndef SMAC_PLANNER_ROS_COMPAT_ROS_TIME_H
#define SMAC_PLANNER_ROS_COMPAT_ROS_TIME_H

#include <chrono>
#include <cstdint>

namespace ros
{

class Duration
{
public:
  Duration() = default;
  explicit Duration(double sec) : sec_(sec) {}
  Duration(int32_t sec, int32_t nsec) : sec_(sec + nsec * 1e-9) {}
  double toSec() const {return sec_;}
  bool operator<(const Duration & other) const {return sec_ < other.sec_;}
  bool operator>(const Duration & other) const {return sec_ > other.sec_;}
  bool operator<=(const Duration & other) const {return sec_ <= other.sec_;}
  bool operator>=(const Duration & other) const {return sec_ >= other.sec_;}
  bool operator==(const Duration & other) const {return sec_ == other.sec_;}

private:
  double sec_{0.0};
};

class Time
{
public:
  Time() = default;
  explicit Time(double sec) : sec_(sec) {}
  static Time now()
  {
    return Time(std::chrono::duration<double>(
        std::chrono::system_clock::now().time_since_epoch()).count());
  }
  double toSec() const {return sec_;}
  Duration operator-(const Time & other) const {return Duration(sec_ - other.sec_);}
  Time operator+(const Duration & d) const {return Time(sec_ + d.toSec());}
  bool operator==(const Time & other) const {return sec_ == other.sec_;}
  bool operator!=(const Time & other) const {return sec_ != other.sec_;}

private:
  double sec_{0.0};
};

}  // namespace ros

#endif
