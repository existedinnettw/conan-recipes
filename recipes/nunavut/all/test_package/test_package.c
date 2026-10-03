#include <demo/Status_1_0.h>
#include <uavcan/node/Heartbeat_1_0.h>

#include <stdio.h>

int main(void) {
    demo_Status_1_0 status;
    demo_Status_1_0_initialize_(&status);
    status.heartbeat.uptime = 0x01020304UL;
    status.heartbeat.health.value = uavcan_node_Health_1_0_NOMINAL;
    status.heartbeat.mode.value = uavcan_node_Mode_1_0_OPERATIONAL;
    status.battery_percent = 87;

    uint8_t buffer[demo_Status_1_0_SERIALIZATION_BUFFER_SIZE_BYTES_];
    size_t size = sizeof(buffer);
    if (demo_Status_1_0_serialize_(&status, buffer, &size) < 0 || size != 4 + 7 + 1) { /* delimiter header, Heartbeat, battery_percent */
        return 1;
    }

    demo_Status_1_0 decoded;
    if (demo_Status_1_0_deserialize_(&decoded, buffer, &size) < 0 ||
        decoded.heartbeat.uptime != status.heartbeat.uptime || decoded.battery_percent != 87) {
        return 1;
    }
    printf("%s: %zu bytes\n", demo_Status_1_0_FULL_NAME_AND_VERSION_, size);
    return 0;
}
