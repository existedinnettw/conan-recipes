#include "isobus/hardware_integration/virtual_can_plugin.hpp"
#include "isobus/isobus/can_message_frame.hpp"
#include "isobus/utility/system_timing.hpp"

int main()
{
    isobus::VirtualCANPlugin interface("conan-test", true);
    interface.open();

    isobus::CANMessageFrame frame{};
    frame.identifier = 0x123;
    frame.dataLength = 0;

    const auto timestamp = isobus::SystemTiming::get_timestamp_ms();
    const bool sent = interface.write_frame(frame);
    interface.close();

    return (sent && (isobus::SystemTiming::get_time_elapsed_ms(timestamp) < 1000)) ? 0 : 1;
}
