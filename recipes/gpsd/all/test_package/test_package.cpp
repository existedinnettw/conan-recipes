#include <cstdio>

#include <gps.h>
#if __has_include(<libgpsmm.h>)
#include <libgpsmm.h>
#endif

int main() {
    // No gpsd needed: only check that libgps (and libgpsmm) link and answer.
#if __has_include(<libgpsmm.h>)
    bool (gpsmm::*is_open)() = &gpsmm::is_open;
    (void)is_open;
#endif
    std::printf("gpsd API %d.%d: %s\n", GPSD_API_MAJOR_VERSION, GPSD_API_MINOR_VERSION, gps_errstr(0));
    return 0;
}
