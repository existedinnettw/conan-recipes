#include <cstdint>

#include <mavlink/common/mavlink.h>

int main()
{
    // Scenario: Pack and decode a MAVLink heartbeat message.
    // Given a heartbeat with known system state.
    mavlink_message_t message{};
    mavlink_msg_heartbeat_pack(
        1,
        MAV_COMP_ID_AUTOPILOT1,
        &message,
        MAV_TYPE_QUADROTOR,
        MAV_AUTOPILOT_GENERIC,
        MAV_MODE_FLAG_SAFETY_ARMED,
        0,
        MAV_STATE_ACTIVE
    );

    // When the generated dialect API decodes the message.
    mavlink_heartbeat_t heartbeat{};
    mavlink_msg_heartbeat_decode(&message, &heartbeat);

    // Then its type and state match the packed values.
    return heartbeat.type == MAV_TYPE_QUADROTOR &&
                   heartbeat.system_status == MAV_STATE_ACTIVE
               ? 0
               : 1;
}
