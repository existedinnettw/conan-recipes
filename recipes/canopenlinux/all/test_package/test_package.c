#include <stdarg.h>
#include <stdio.h>

#include "CANopen.h"
#include "CO_epoll_interface.h"
#include "OD.h"

void log_printf(int priority, const char *format, ...) {
    (void)priority;
    va_list arguments;
    va_start(arguments, format);
    (void)vfprintf(stderr, format, arguments);
    va_end(arguments);
}

static void application_realtime_task(CO_t *instance) {
    (void)instance;
}

static int application_main_task(void) {
    uint32_t heap_memory_used = 0;
    CO_config_t config = {0};
    OD_INIT_CONFIG(config);

    CO_t *instance = CO_new(&config, &heap_memory_used);
    if (instance == NULL || OD == NULL) {
        return 1;
    }

    CO_epoll_t epoll = {0};
    if (CO_epoll_create(&epoll, 1000) != CO_ERROR_NO) {
        CO_delete(instance);
        return 1;
    }

    application_realtime_task(instance);
    CO_epoll_close(&epoll);
    CO_delete(instance);
    return 0;
}

int main(void) { return application_main_task(); }
