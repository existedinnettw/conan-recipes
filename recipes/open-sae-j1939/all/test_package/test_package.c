#include <stddef.h>

#include "Open_SAE_J1939/Open_SAE_J1939.h"

int main(void) {
    ENUM_J1939_RX_MSG (*listener)(J1939 *) = Open_SAE_J1939_Listen_For_Messages;
    return listener == NULL;
}
