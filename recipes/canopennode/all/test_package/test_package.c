#include "CANopen.h"
#include "OD.h"

int main(void) {
    uint32_t heap_memory_used = 0;
    CO_config_t config = {0};
    OD_INIT_CONFIG(config);

    CO_t *instance = CO_new(&config, &heap_memory_used);
    if (instance == NULL || OD == NULL) {
        return 1;
    }

    CO_delete(instance);
    return 0;
}
