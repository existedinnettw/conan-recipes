#include <udpard.h>
#include <uavcan/node/Heartbeat_1_0.h>

#include <stdio.h>
#include <stdlib.h>

static void* allocate(void* const user_reference, const size_t size) {
    (void)user_reference;
    return malloc(size);
}

static void deallocate(void* const user_reference, const size_t size, void* const pointer) {
    (void)user_reference;
    (void)size;
    free(pointer);
}

int main(void) {
    uavcan_node_Heartbeat_1_0 heartbeat;
    uavcan_node_Heartbeat_1_0_initialize_(&heartbeat);
    heartbeat.mode.value = uavcan_node_Mode_1_0_OPERATIONAL;
    uint8_t serialized[uavcan_node_Heartbeat_1_0_SERIALIZATION_BUFFER_SIZE_BYTES_];
    size_t serialized_size = sizeof(serialized);
    if (uavcan_node_Heartbeat_1_0_serialize_(&heartbeat, serialized, &serialized_size) < 0) {
        return 1;
    }

    const struct UdpardMemoryResource memory = {NULL, deallocate, allocate};
    const struct UdpardTxMemoryResources tx_memory = {memory, memory};
    const UdpardNodeID node_id = 42;
    struct UdpardTx tx;
    if (udpardTxInit(&tx, &node_id, 16, tx_memory) != 0) {
        return 1;
    }

    const struct UdpardPayload payload = {.size = serialized_size, .data = serialized};
    if (udpardTxPublish(&tx, 1000000, UdpardPriorityNominal, uavcan_node_Heartbeat_1_0_FIXED_PORT_ID_, 0, payload,
                        NULL) != 1) {
        return 1;
    }

    struct UdpardTxItem* item = udpardTxPeek(&tx);
    if (item == NULL || item->datagram_payload.size <= serialized_size) {
        return 1;
    }
    const uint32_t ip = item->destination.ip_address;
    printf("libudpard %d.%d: Heartbeat datagram of %zu bytes to %u.%u.%u.%u:%u\n", UDPARD_VERSION_MAJOR,
           UDPARD_VERSION_MINOR, item->datagram_payload.size, (unsigned)(ip >> 24) & 0xFFU,
           (unsigned)(ip >> 16) & 0xFFU, (unsigned)(ip >> 8) & 0xFFU, (unsigned)ip & 0xFFU,
           (unsigned)item->destination.udp_port);
    udpardTxFree(tx_memory, udpardTxPop(&tx, item));
    return tx.queue_size == 0 ? 0 : 1;
}
