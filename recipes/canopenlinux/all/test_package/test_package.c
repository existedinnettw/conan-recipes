#include "CO_epoll_interface.h"
#include "CO_storageLinux.h"

void test_package_type_check(CO_epoll_t *epoll, CO_storage_t *storage) {
    CO_epoll_close(epoll);
    (void)CO_storageLinux_auto_process(storage, false);
}

