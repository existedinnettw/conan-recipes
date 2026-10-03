#include <canard.h>
#ifdef WITH_SOCKETCAN
#include <socketcan.h>
#endif

#include <stdio.h>

/* uavcan.protocol.NodeStatus */
#define NODE_STATUS_DATA_TYPE_ID 341
#define NODE_STATUS_DATA_TYPE_SIGNATURE 0x0f0868d0c1a7c6f1ULL

static void on_reception(CanardInstance* ins, CanardRxTransfer* transfer) {
    (void)ins;
    (void)transfer;
}

static bool should_accept(const CanardInstance* ins, uint64_t* out_data_type_signature,
                          uint16_t data_type_id, CanardTransferType transfer_type,
                          uint8_t source_node_id) {
    (void)ins;
    (void)out_data_type_signature;
    (void)data_type_id;
    (void)transfer_type;
    (void)source_node_id;
    return false;
}

int main(void) {
    static uint8_t arena[1024];
    CanardInstance canard;
    canardInit(&canard, arena, sizeof(arena), on_reception, should_accept, NULL);
    canardSetLocalNodeID(&canard, 42);

    uint8_t payload[7] = {0};
    uint8_t transfer_id = 0;
    CanardTxTransfer transfer;
    canardInitTxTransfer(&transfer);
    transfer.transfer_type = CanardTransferTypeBroadcast;
    transfer.data_type_signature = NODE_STATUS_DATA_TYPE_SIGNATURE;
    transfer.data_type_id = NODE_STATUS_DATA_TYPE_ID;
    transfer.inout_transfer_id = &transfer_id;
    transfer.priority = CANARD_TRANSFER_PRIORITY_LOW;
    transfer.payload = payload;
    transfer.payload_len = sizeof(payload);

    if (canardBroadcastObj(&canard, &transfer) != 1) {
        return 1;
    }
    const CanardCANFrame* frame = canardPeekTxQueue(&canard);
    if (frame == NULL || frame->data_len != sizeof(payload) + 1) {
        return 1;
    }
    printf("libcanard %d.%d: NodeStatus frame id 0x%08x\n", CANARD_VERSION_MAJOR, CANARD_VERSION_MINOR,
           (unsigned)(frame->id & CANARD_CAN_EXT_ID_MASK));
    canardPopTxQueue(&canard);

#ifdef WITH_SOCKETCAN
    (void)&socketcanInit;
#endif
    return 0;
}
