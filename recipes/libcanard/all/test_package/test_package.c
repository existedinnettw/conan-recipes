#include <canard.h>
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
    const struct CanardMemoryResource memory = {NULL, deallocate, allocate};
    struct CanardInstance canard = canardInit(memory);
    canard.node_id = 42;
    struct CanardTxQueue queue = canardTxInit(16, CANARD_MTU_CAN_CLASSIC, memory);

    uavcan_node_Heartbeat_1_0 heartbeat;
    uavcan_node_Heartbeat_1_0_initialize_(&heartbeat);
    heartbeat.mode.value = uavcan_node_Mode_1_0_OPERATIONAL;
    uint8_t serialized[uavcan_node_Heartbeat_1_0_SERIALIZATION_BUFFER_SIZE_BYTES_];
    size_t serialized_size = sizeof(serialized);
    if (uavcan_node_Heartbeat_1_0_serialize_(&heartbeat, serialized, &serialized_size) < 0) {
        return 1;
    }

    const struct CanardTransferMetadata metadata = {
        .priority = CanardPriorityNominal,
        .transfer_kind = CanardTransferKindMessage,
        .port_id = uavcan_node_Heartbeat_1_0_FIXED_PORT_ID_,
        .remote_node_id = CANARD_NODE_ID_UNSET,
        .transfer_id = 0,
    };
    const struct CanardPayload payload = {.size = serialized_size, .data = serialized};
    if (canardTxPush(&queue, &canard, 0, &metadata, payload, 0, NULL) != 1) {
        return 1;
    }

    struct CanardTxQueueItem* item = canardTxPeek(&queue);
    if (item == NULL || item->frame.payload.size != serialized_size + 1) {
        return 1;
    }
    printf("libcanard %d.%d: Heartbeat frame id 0x%08x\n", CANARD_VERSION_MAJOR, CANARD_VERSION_MINOR,
           (unsigned)item->frame.extended_can_id);
    canardTxFree(&queue, &canard, canardTxPop(&queue, item));
    return queue.size == 0 ? 0 : 1;
}
