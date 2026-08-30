#include "CANopen.h"

CO_t *test_package_type_check(CO_config_t *config, uint32_t *heap_memory_used) {
    return CO_new(config, heap_memory_used);
}
