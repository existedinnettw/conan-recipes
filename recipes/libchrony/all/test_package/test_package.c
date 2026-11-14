#include <stdio.h>

#include <chrony.h>

int main(void) {
    /* No chronyd needed: only check that the library links and answers. */
    int n = chrony_get_number_supported_reports();
    printf("libchrony supports %d reports, first: %s\n", n, chrony_get_report_name(0));
    return n > 0 ? 0 : 1;
}
