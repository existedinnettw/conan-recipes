#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include <marnav/ais/ais.hpp>
#include <marnav/ais/message_05.hpp>
#include <marnav/nmea/ais_helper.hpp>
#include <marnav/nmea/io.hpp>
#include <marnav/nmea/nmea.hpp>
#include <marnav/nmea/rmc.hpp>
#include <marnav/version.hpp>

#ifdef HAVE_MARNAV_IO
#include <marnav-io/serial.hpp>
#endif

int main() {
    using namespace marnav;

    std::cout << "marnav " << get_meta().project_version << "\n";

    // NMEA-0183 sentence parsing.
    auto rmc = nmea::sentence_cast<nmea::rmc>(nmea::make_sentence(
        "$GPRMC,201034,A,4702.4040,N,00818.3281,E,0.0,328.4,260807,0.6,E,A*17"));
    std::cout << "RMC lat " << nmea::to_string(rmc->get_lat())
              << " lon " << nmea::to_string(rmc->get_lon()) << "\n";

    // AIS message decoding from a two-part VDM.
    std::vector<std::unique_ptr<nmea::sentence>> sentences;
    for (const auto & txt : {
             "!AIVDM,2,1,3,B,55P5TL01VIaAL@7WKO@mBplU@<PDhh000000001S;AJ::4A80?4i@E53,0*3E",
             "!AIVDM,2,2,3,B,1@0000000000000,2*55"}) {
        sentences.push_back(nmea::make_sentence(txt));
    }
    auto message = ais::make_message(nmea::collect_payload(sentences.begin(), sentences.end()));
    auto report = ais::message_cast<ais::message_05>(message);
    std::cout << "AIS shipname " << report->get_shipname() << "\n";

#ifdef HAVE_MARNAV_IO
    // Construct only: opening a serial device needs hardware.
    io::serial port("/dev/null", io::serial::baud::baud_4800, io::serial::databits::bit_8,
                    io::serial::stopbits::bit_1, io::serial::parity::none);
#endif

    return report->get_shipname().empty() ? EXIT_FAILURE : EXIT_SUCCESS;
}
