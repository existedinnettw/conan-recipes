#include <rtdm/can.h>

int main(void)
{
    struct can_frame frame = { .can_id = 0x080, .can_dlc = 0 };
    struct sockaddr_can address = { .can_family = AF_CAN };

    return frame.can_id == 0x080 && address.can_family == AF_CAN ? 0 : 1;
}
