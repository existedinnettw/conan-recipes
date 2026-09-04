// Generated from MAVROS libmavconn/src/mavlink_helpers.cpp.em.
// SPDX-License-Identifier: BSD-3-Clause

#include <cstring>
#include <string>
#include <vector>

#include "mavconn/console_bridge_compat.hpp"
#include "mavconn/interface.hpp"

using mavconn::MAVConnInterface;

void MAVConnInterface::init_msg_entry()
{
  auto load = [&](const char * dialect, const mavlink::mavlink_msg_entry_t & e) {
      auto it = message_entries.find(e.msgid);
      if (it == message_entries.end()) {
        message_entries[e.msgid] = &e;
      } else if (memcmp(&e, it->second, sizeof(e)) != 0) {
        CONSOLE_BRIDGE_logDebug(
          "mavconn: init: message from %s, MSG-ID %d ignored; table has different entry",
          dialect, e.msgid);
      }
    };

  for (auto & e : mavlink::common::MESSAGE_ENTRIES) load("common", e);
  for (auto & e : mavlink::ardupilotmega::MESSAGE_ENTRIES) load("ardupilotmega", e);
}

std::vector<std::string> MAVConnInterface::get_known_dialects()
{
  return {"common", "ardupilotmega"};
}

const mavlink::mavlink_msg_entry_t * mavlink::mavlink_get_msg_entry(uint32_t msgid)
{
  auto it = MAVConnInterface::message_entries.find(msgid);
  return it != MAVConnInterface::message_entries.end() ? it->second : nullptr;
}
