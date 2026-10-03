#include <libobsensor/ObSensor.hpp>

#include <iostream>

int main() {
    std::cout << "OrbbecSDK " << ob::Version::getMajor() << "." << ob::Version::getMinor() << "."
              << ob::Version::getPatch() << " (" << ob::Version::getStageVersion() << ")" << std::endl;

    // Creating a context loads the extensions and enumerates devices; none are attached in CI.
    ob::Context::setLoggerSeverity(OB_LOG_SEVERITY_WARN);
    ob::Context context;
    auto devices = context.queryDeviceList();
    std::cout << "devices found: " << devices->getCount() << std::endl;

    auto filter = std::make_shared<ob::DecimationFilter>();
    std::cout << "filter: " << filter->getName() << std::endl;

    // SpatialAdvancedFilter comes from the prebuilt filter extension, so this throws unless
    // the SDK finds the extensions packaged next to its library. Creating it needs a device
    // to activate the extension.
    std::cout << "SpatialAdvancedFilter vendor code: '" << ob::FilterFactory::getFilterVendorSpecificCode("SpatialAdvancedFilter")
              << "'" << std::endl;
    return 0;
}
