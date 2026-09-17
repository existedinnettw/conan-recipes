#include <stdio.h>

#include <evl/thread.h>
#include <evl/version.h>

int main(void)
{
    struct evl_version version = evl_get_version();

    /* Attaching a thread would need a running EVL core, so only report here. */
    printf("%s (API %d, requires ABI %d)\n",
           version.version_string,
           version.api_level,
           version.abi_level);

    return version.abi_level == EVL_ABI_PREREQ ? 0 : 1;
}
