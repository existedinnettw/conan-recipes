#include <stdio.h>

#include <rtklib.h>

/* RTKLIB applications may provide their own progress callback; the library
 * must not clash with it. settspan() and settime() come from the library. */
int showmsg(const char *format, ...) {
    (void)format;
    return 0;
}

int main(void) {
    const double ep[6] = {2024, 8, 22, 11, 0, 0};
    char str[64], id[8];
    gtime_t t = epoch2time(ep);
    int week;
    double tow = time2gpst(t, &week);

    time2str(t, str, 0);
    satno2id(satno(SYS_GAL, 11), id);
    printf("RTKLIB %s %s: %s = GPS week %d tow %.0f, %s, NFREQ=%d\n", VER_RTKLIB, PATCH_LEVEL,
           str, week, tow, id, NFREQ);

    return week == 2328 && tow == 385200.0 && id[0] == 'E' ? 0 : 1;
}
