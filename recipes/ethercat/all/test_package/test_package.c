#include <ecrt.h>

#include <stdio.h>

int main(void)
{
    printf("ECRT version magic: %u\n", ecrt_version_magic());
    return 0;
}
