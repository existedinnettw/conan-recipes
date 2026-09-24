#include <stdio.h>
#include <string.h>

#include <nmea.h>
#include <nmea/gpgll.h>

int main(void) {
    char sentence[] = "$GPGLL,4916.45,N,12311.12,W,225444,A,*1D\r\n";
    nmea_s *data = nmea_parse(sentence, strlen(sentence), 0);
    if (data == NULL || data->type != NMEA_GPGLL) {
        fprintf(stderr, "failed to parse GPGLL sentence\n");
        return 1;
    }

    nmea_gpgll_s *gpgll = (nmea_gpgll_s *)data;
    int ok = gpgll->latitude.degrees == 49 && gpgll->latitude.cardinal == NMEA_CARDINAL_DIR_NORTH &&
             gpgll->longitude.degrees == 123 && gpgll->longitude.cardinal == NMEA_CARDINAL_DIR_WEST;
    printf("GPGLL: %d %c, %d %c\n", gpgll->latitude.degrees, (char)gpgll->latitude.cardinal,
           gpgll->longitude.degrees, (char)gpgll->longitude.cardinal);
    nmea_free(data);
    return ok ? 0 : 1;
}
