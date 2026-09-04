// Generated from MAVROS libmavconn/include/mavconn/mavlink_dialect.hpp.em.
// SPDX-License-Identifier: BSD-3-Clause

#pragma once
#ifndef MAVCONN__MAVLINK_DIALECT_HPP_
#define MAVCONN__MAVLINK_DIALECT_HPP_

namespace mavlink
{
#ifndef MAVLINK_VERSION
#include <mavlink/config.h>
constexpr auto version = MAVLINK_VERSION;
#undef MAVLINK_VERSION
#else
constexpr auto version = "unknown";
#endif
}  // namespace mavlink

#define MAVLINK_START_SIGN_STREAM(link_id)
#define MAVLINK_END_SIGN_STREAM(link_id)

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wpedantic"
#include <mavlink/v2.0/common/common.hpp>
#include <mavlink/v2.0/ardupilotmega/ardupilotmega.hpp>
#pragma GCC diagnostic pop

#endif  // MAVCONN__MAVLINK_DIALECT_HPP_
