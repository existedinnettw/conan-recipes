#include <ixblue_stdbin_decoder/stdbin_decoder.h>

#include <cmath>
#include <cstdint>
#include <iostream>
#include <vector>

int main()
{
    // Minimal V2 navigation frame carrying only attitude and heading, after
    // upstream's test/datasets/MinimalV2NavFrame.h but with the floats in the
    // protocol's big-endian order. The checksum is a byte sum, so it is unchanged.
    const std::vector<uint8_t> frame{
        'I',  'X',                    // iXblue header
        0x02,                         // protocol version
        0x00, 0x00, 0x00, 0x01,       // navigation bitmask: AttitudeAndHeading
        0x00, 0x00, 0x00, 0x00,       // external data bitmask
        0x00, 0x25,                   // telegram size
        0x00, 0x00, 0x00, 0x05,       // navigation validity time
        0x00, 0x00, 0x01, 0x23,       // counter
        0x3f, 0xa0, 0x00, 0x00,       // heading: 1.25f
        0xbf, 0xc0, 0x00, 0x00,       // roll: -1.5f
        0x41, 0x48, 0xcc, 0xcd,       // pitch: 12.55f
        0x00, 0x00, 0x05, 0x72,       // checksum
    };

    ixblue_stdbin_decoder::StdBinDecoder decoder;
    decoder.addNewData(frame);
    if(!decoder.parseNextFrame())
    {
        std::cerr << "frame was not parsed\n";
        return 1;
    }

    const auto nav = decoder.getLastNavData();
    if(!nav.attitudeHeading.is_initialized())
    {
        std::cerr << "attitude and heading missing\n";
        return 1;
    }

    const auto& att = nav.attitudeHeading.get();
    std::cout << "heading " << att.heading_deg << " roll " << att.roll_deg << " pitch "
              << att.pitch_deg << '\n';
    const bool ok = att.heading_deg == 1.25f && att.roll_deg == -1.5f &&
                    std::fabs(att.pitch_deg - 12.55f) < 1e-5f;
    return ok ? 0 : 1;
}
