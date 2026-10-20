#include <stdio.h>
#include <stdlib.h>

#include "co_core.h"

/* Drivers that do nothing: enough to bring a node up without CAN hardware. */
static void     CanInit(void) {}
static void     CanEnable(uint32_t baudrate) { (void)baudrate; }
static int16_t  CanRead(CO_IF_FRM *frm) { (void)frm; return 0; }
static int16_t  CanSend(CO_IF_FRM *frm) { (void)frm; return (int16_t)sizeof(CO_IF_FRM); }
static void     CanReset(void) {}
static void     CanClose(void) {}

static void     TmrInit(uint32_t freq) { (void)freq; }
static void     TmrReload(uint32_t reload) { (void)reload; }
static uint32_t TmrDelay(void) { return 0u; }
static void     TmrStop(void) {}
static void     TmrStart(void) {}
static uint8_t  TmrUpdate(void) { return 0u; }

static void     NvmInit(void) {}
static uint32_t NvmRead(uint32_t start, uint8_t *buf, uint32_t size) { (void)start; (void)buf; return size; }
static uint32_t NvmWrite(uint32_t start, uint8_t *buf, uint32_t size) { (void)start; (void)buf; return size; }

static const CO_IF_CAN_DRV   CanDriver = { CanInit, CanEnable, CanRead, CanSend, CanReset, CanClose };
static const CO_IF_TIMER_DRV TmrDriver = { TmrInit, TmrReload, TmrDelay, TmrStop, TmrStart, TmrUpdate };
static const CO_IF_NVM_DRV   NvmDriver = { NvmInit, NvmRead, NvmWrite };
static struct CO_IF_DRV_T    AppDriver = { &CanDriver, &TmrDriver, &NvmDriver };

static uint8_t        Obj1001 = 0;
static const uint32_t Obj1000 = 0x00000000L;
static const uint32_t Obj1014 = 0x00000080L;
static uint16_t       Obj1017 = 0;
static const uint32_t Obj1018_01 = 0x00000000L;
static const uint32_t Obj1018_02 = 0x00000000L;
static const uint32_t Obj1018_03 = 0x00000000L;
static const uint32_t Obj1018_04 = 0x00000000L;
static const uint32_t Obj1200_01 = CO_COBID_SDO_REQUEST();
static const uint32_t Obj1200_02 = CO_COBID_SDO_RESPONSE();

#define APP_OBJ_N 16u
static struct CO_OBJ_T AppOD[APP_OBJ_N] = {
    {CO_KEY(0x1000, 0, CO_OBJ_____R_), CO_TUNSIGNED32, (CO_DATA)(&Obj1000)},
    {CO_KEY(0x1001, 0, CO_OBJ_____R_), CO_TUNSIGNED8,  (CO_DATA)(&Obj1001)},
    {CO_KEY(0x1014, 0, CO_OBJ_____R_), CO_TEMCY_ID,    (CO_DATA)(&Obj1014)},
    {CO_KEY(0x1017, 0, CO_OBJ_____RW), CO_THB_PROD,    (CO_DATA)(&Obj1017)},
    /* LSS identifies the node by the identity object 1018h. */
    {CO_KEY(0x1018, 0, CO_OBJ_D___R_), CO_TUNSIGNED8,  (CO_DATA)(4)},
    {CO_KEY(0x1018, 1, CO_OBJ_____R_), CO_TUNSIGNED32, (CO_DATA)(&Obj1018_01)},
    {CO_KEY(0x1018, 2, CO_OBJ_____R_), CO_TUNSIGNED32, (CO_DATA)(&Obj1018_02)},
    {CO_KEY(0x1018, 3, CO_OBJ_____R_), CO_TUNSIGNED32, (CO_DATA)(&Obj1018_03)},
    {CO_KEY(0x1018, 4, CO_OBJ_____R_), CO_TUNSIGNED32, (CO_DATA)(&Obj1018_04)},
    {CO_KEY(0x1200, 0, CO_OBJ_D___R_), CO_TUNSIGNED8,  (CO_DATA)(2)},
    {CO_KEY(0x1200, 1, CO_OBJ__N__R_), CO_TUNSIGNED32, (CO_DATA)(&Obj1200_01)},
    {CO_KEY(0x1200, 2, CO_OBJ__N__R_), CO_TUNSIGNED32, (CO_DATA)(&Obj1200_02)},
    CO_OBJ_DICT_ENDMARK
};

#define APP_TMR_N 4u
static CO_TMR_MEM  TmrMem[APP_TMR_N];
static uint8_t     SdoSrvMem[CO_SSDO_N * CO_SDO_BUF_BYTE];
static CO_EMCY_TBL EmcyTbl[1] = { { CO_EMCY_REG_GENERAL, CO_EMCY_CODE_GEN_ERR } };

static struct CO_NODE_SPEC_T AppSpec = {
    1u, 250000u, &AppOD[0], APP_OBJ_N, &EmcyTbl[0],
    &TmrMem[0], APP_TMR_N, 1000u, &AppDriver, &SdoSrvMem[0]
};

/* Overrides the library's weak default, which would spin forever. */
void CONodeFatalError(void)
{
    fprintf(stderr, "CANopen fatal error\n");
    exit(1);
}

int main(void)
{
    static CO_NODE node;
    uint8_t        nmt_error;
    CO_ERR         err;

    CONodeInit(&node, &AppSpec);
    err = CONodeGetErr(&node);
    if (err != CO_ERR_NONE) {
        fprintf(stderr, "CONodeInit failed: %d\n", (int)err);
        return 1;
    }

    CONodeStart(&node);
    CONmtSetMode(&node.Nmt, CO_OPERATIONAL);
    CONodeProcess(&node);
    COTmrProcess(&node.Tmr);

    if (CODictRdByte(&node.Dict, CO_DEV(0x1001, 0), &nmt_error) != CO_ERR_NONE) {
        fprintf(stderr, "failed to read object 1001h\n");
        return 1;
    }

    printf("canopen-stack node %u is %s\n", (unsigned)CONmtGetNodeId(&node.Nmt),
           CONmtGetMode(&node.Nmt) == CO_OPERATIONAL ? "operational" : "not operational");
    CONodeStop(&node);
    return 0;
}
