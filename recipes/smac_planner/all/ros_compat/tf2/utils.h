#ifndef SMAC_PLANNER_ROS_COMPAT_TF2_UTILS_H
#define SMAC_PLANNER_ROS_COMPAT_TF2_UTILS_H

#include <algorithm>
#include <cmath>

#include "geometry_msgs/Quaternion.h"

// The parts of tf2 (LinearMath, utils.h, tf2_geometry_msgs) that smac_planner uses,
// with tf2's conventions.
namespace tf2
{

class Quaternion
{
public:
  Quaternion() = default;
  Quaternion(double x, double y, double z, double w) : x_(x), y_(y), z_(z), w_(w) {}

  double x() const {return x_;}
  double y() const {return y_;}
  double z() const {return z_;}
  double w() const {return w_;}

  void setValue(double x, double y, double z, double w)
  {
    x_ = x;
    y_ = y;
    z_ = z;
    w_ = w;
  }

  // Fixed axes: roll about X, pitch about Y, yaw about Z.
  void setRPY(double roll, double pitch, double yaw)
  {
    const double half_yaw = yaw * 0.5, half_pitch = pitch * 0.5, half_roll = roll * 0.5;
    const double cos_yaw = std::cos(half_yaw), sin_yaw = std::sin(half_yaw);
    const double cos_pitch = std::cos(half_pitch), sin_pitch = std::sin(half_pitch);
    const double cos_roll = std::cos(half_roll), sin_roll = std::sin(half_roll);
    setValue(
      sin_roll * cos_pitch * cos_yaw - cos_roll * sin_pitch * sin_yaw,
      cos_roll * sin_pitch * cos_yaw + sin_roll * cos_pitch * sin_yaw,
      cos_roll * cos_pitch * sin_yaw - sin_roll * sin_pitch * cos_yaw,
      cos_roll * cos_pitch * cos_yaw + sin_roll * sin_pitch * sin_yaw);
  }

  // As tf2: yaw about Y, pitch about X, roll about Z.
  void setEuler(double yaw, double pitch, double roll)
  {
    const double half_yaw = yaw * 0.5, half_pitch = pitch * 0.5, half_roll = roll * 0.5;
    const double cos_yaw = std::cos(half_yaw), sin_yaw = std::sin(half_yaw);
    const double cos_pitch = std::cos(half_pitch), sin_pitch = std::sin(half_pitch);
    const double cos_roll = std::cos(half_roll), sin_roll = std::sin(half_roll);
    setValue(
      cos_roll * sin_pitch * cos_yaw + sin_roll * cos_pitch * sin_yaw,
      cos_roll * cos_pitch * sin_yaw - sin_roll * sin_pitch * cos_yaw,
      sin_roll * cos_pitch * cos_yaw - cos_roll * sin_pitch * sin_yaw,
      cos_roll * cos_pitch * cos_yaw + sin_roll * sin_pitch * sin_yaw);
  }

private:
  double x_{0.0};
  double y_{0.0};
  double z_{0.0};
  double w_{1.0};
};

class Matrix3x3
{
public:
  explicit Matrix3x3(const Quaternion & q) : q_(q) {}

  void getRPY(double & roll, double & pitch, double & yaw) const
  {
    const double x = q_.x(), y = q_.y(), z = q_.z(), w = q_.w();
    const double d = x * x + y * y + z * z + w * w;
    const double s = 2.0 / d;
    const double xs = x * s, ys = y * s, zs = z * s;
    const double wx = w * xs, wy = w * ys, wz = w * zs;
    const double xx = x * xs, xy = x * ys, xz = x * zs;
    const double yy = y * ys, yz = y * zs, zz = z * zs;
    // rows of the rotation matrix that tf2's getEulerYPR reads
    const double m00 = 1.0 - (yy + zz), m10 = xy + wz, m20 = xz - wy;
    const double m21 = yz + wx, m22 = 1.0 - (xx + yy);
    if (std::fabs(m20) >= 1.0) {
      yaw = 0.0;
      const double m01 = xy - wz, m02 = xz + wy;
      if (m20 < 0.0) {
        pitch = M_PI / 2.0;
        roll = std::atan2(m01, m02);
      } else {
        pitch = -M_PI / 2.0;
        roll = std::atan2(-m01, -m02);
      }
    } else {
      pitch = -std::asin(m20);
      const double cos_pitch = std::cos(pitch);
      roll = std::atan2(m21 / cos_pitch, m22 / cos_pitch);
      yaw = std::atan2(m10 / cos_pitch, m00 / cos_pitch);
    }
  }

private:
  Quaternion q_;
};

inline double getYaw(const Quaternion & q)
{
  const double sqw = q.w() * q.w(), sqx = q.x() * q.x(), sqy = q.y() * q.y(), sqz = q.z() * q.z();
  const double sarg = -2.0 * (q.x() * q.z() - q.w() * q.y()) / (sqx + sqy + sqz + sqw);
  if (sarg <= -0.99999) {
    return -2.0 * std::atan2(q.y(), q.x());
  } else if (sarg >= 0.99999) {
    return 2.0 * std::atan2(q.y(), q.x());
  }
  return std::atan2(2.0 * (q.x() * q.y() + q.w() * q.z()), sqw + sqx - sqy - sqz);
}

inline double getYaw(const geometry_msgs::Quaternion & q)
{
  return getYaw(Quaternion(q.x, q.y, q.z, q.w));
}

inline geometry_msgs::Quaternion toMsg(const Quaternion & q)
{
  geometry_msgs::Quaternion msg;
  msg.x = q.x();
  msg.y = q.y();
  msg.z = q.z();
  msg.w = q.w();
  return msg;
}

inline void fromMsg(const geometry_msgs::Quaternion & msg, Quaternion & q)
{
  q.setValue(msg.x, msg.y, msg.z, msg.w);
}

}  // namespace tf2

#endif
