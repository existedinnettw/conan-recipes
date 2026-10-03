#include <libobsensor/ObSensor.h>

#include <stdio.h>

int main(void) {
    printf("OrbbecSDK C API %d.%d.%d\n", ob_get_major_version(), ob_get_minor_version(), ob_get_patch_version());
    return ob_get_major_version() == 2 ? 0 : 1;
}
