#ifndef SMAC_PLANNER_ROS_COMPAT_ROS_CONSOLE_H
#define SMAC_PLANNER_ROS_COMPAT_ROS_CONSOLE_H

// rosconsole's macros, printing to stderr. DEBUG messages are dropped.

#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <sstream>
#include <string>

namespace ros_compat
{
inline void log(const char * level, const char * format, ...)
{
  std::fprintf(stderr, "[%s] [smac_planner] ", level);
  va_list args;
  va_start(args, format);
  std::vfprintf(stderr, format, args);
  va_end(args);
  std::fputc('\n', stderr);
}

inline void log(const char * level, const std::string & message)
{
  log(level, "%s", message.c_str());
}

inline double steadySeconds()
{
  return std::chrono::duration<double>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
}
}  // namespace ros_compat

#define ROS_COMPAT_LOG(level, ...) ::ros_compat::log(level, __VA_ARGS__)
#define ROS_COMPAT_LOG_STREAM(level, args) \
  do { \
    std::ostringstream ros_compat_stream; \
    ros_compat_stream << args; \
    ::ros_compat::log(level, ros_compat_stream.str()); \
  } while (0)
#define ROS_COMPAT_LOG_ONCE(level, ...) \
  do { \
    static bool ros_compat_logged = false; \
    if (!ros_compat_logged) { \
      ros_compat_logged = true; \
      ::ros_compat::log(level, __VA_ARGS__); \
    } \
  } while (0)
#define ROS_COMPAT_LOG_STREAM_ONCE(level, args) \
  do { \
    static bool ros_compat_logged = false; \
    if (!ros_compat_logged) { \
      ros_compat_logged = true; \
      ROS_COMPAT_LOG_STREAM(level, args); \
    } \
  } while (0)
#define ROS_COMPAT_LOG_THROTTLE(period, level, ...) \
  do { \
    static double ros_compat_last = -1.0e300; \
    const double ros_compat_now = ::ros_compat::steadySeconds(); \
    if (ros_compat_now - ros_compat_last >= (period)) { \
      ros_compat_last = ros_compat_now; \
      ::ros_compat::log(level, __VA_ARGS__); \
    } \
  } while (0)

#define ROS_COMPAT_NOOP(...) do {} while (0)

#define ROS_DEBUG(...) ROS_COMPAT_NOOP(__VA_ARGS__)
#define ROS_DEBUG_NAMED(name, ...) ROS_COMPAT_NOOP(__VA_ARGS__)
#define ROS_DEBUG_STREAM(args) ROS_COMPAT_NOOP()
#define ROS_DEBUG_ONCE(...) ROS_COMPAT_NOOP(__VA_ARGS__)
#define ROS_DEBUG_THROTTLE(period, ...) ROS_COMPAT_NOOP(__VA_ARGS__)

#define ROS_INFO(...) ROS_COMPAT_LOG("INFO", __VA_ARGS__)
#define ROS_WARN(...) ROS_COMPAT_LOG("WARN", __VA_ARGS__)
#define ROS_ERROR(...) ROS_COMPAT_LOG("ERROR", __VA_ARGS__)
#define ROS_FATAL(...) ROS_COMPAT_LOG("FATAL", __VA_ARGS__)

#define ROS_INFO_NAMED(name, ...) ROS_COMPAT_LOG("INFO", __VA_ARGS__)
#define ROS_WARN_NAMED(name, ...) ROS_COMPAT_LOG("WARN", __VA_ARGS__)
#define ROS_ERROR_NAMED(name, ...) ROS_COMPAT_LOG("ERROR", __VA_ARGS__)

#define ROS_INFO_STREAM(args) ROS_COMPAT_LOG_STREAM("INFO", args)
#define ROS_WARN_STREAM(args) ROS_COMPAT_LOG_STREAM("WARN", args)
#define ROS_ERROR_STREAM(args) ROS_COMPAT_LOG_STREAM("ERROR", args)

#define ROS_INFO_ONCE(...) ROS_COMPAT_LOG_ONCE("INFO", __VA_ARGS__)
#define ROS_WARN_ONCE(...) ROS_COMPAT_LOG_ONCE("WARN", __VA_ARGS__)
#define ROS_ERROR_ONCE(...) ROS_COMPAT_LOG_ONCE("ERROR", __VA_ARGS__)

#define ROS_INFO_STREAM_ONCE(args) ROS_COMPAT_LOG_STREAM_ONCE("INFO", args)
#define ROS_WARN_STREAM_ONCE(args) ROS_COMPAT_LOG_STREAM_ONCE("WARN", args)
#define ROS_ERROR_STREAM_ONCE(args) ROS_COMPAT_LOG_STREAM_ONCE("ERROR", args)

#define ROS_INFO_THROTTLE(period, ...) ROS_COMPAT_LOG_THROTTLE(period, "INFO", __VA_ARGS__)
#define ROS_WARN_THROTTLE(period, ...) ROS_COMPAT_LOG_THROTTLE(period, "WARN", __VA_ARGS__)
#define ROS_ERROR_THROTTLE(period, ...) ROS_COMPAT_LOG_THROTTLE(period, "ERROR", __VA_ARGS__)

#endif
