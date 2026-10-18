#include <stdio.h>

#include <oplk/oplk.h>
#include <obdcreate/obdcreate.h>

int main(void)
{
    tObdInitParam obdInitParam;
    tOplkError    ret;

    printf("openPOWERLINK %s\n", oplk_getVersionString());

    ret = obdcreate_initObd(&obdInitParam);
    if (ret != kErrorOk)
    {
        fprintf(stderr, "obdcreate_initObd failed: 0x%X\n", ret);
        return 1;
    }

    ret = oplk_initialize();
    if (ret != kErrorOk)
    {
        fprintf(stderr, "oplk_initialize failed: 0x%X\n", ret);
        return 1;
    }
    oplk_exit();
    return 0;
}
