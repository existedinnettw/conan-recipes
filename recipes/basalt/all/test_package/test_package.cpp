#include <basalt/image/image.h>
#include <basalt/utils/keypoints.h>
#include <basalt/utils/vio_config.h>

#include <cstdio>
#include <iostream>
#include <vector>

int main()
{
    // Deterministic texture of random 5x5 blocks: plenty of FAST corners in every cell.
    basalt::ManagedImage<uint16_t> img(320, 240);
    uint32_t state = 12345;
    std::vector<uint16_t> blocks((img.w / 5 + 1) * (img.h / 5 + 1));
    for (auto& b : blocks) {
        state = state * 1664525u + 1013904223u;
        b = static_cast<uint16_t>(state >> 16);
    }
    for (size_t y = 0; y < img.h; ++y) {
        for (size_t x = 0; x < img.w; ++x) {
            img(x, y) = blocks[(y / 5) * (img.w / 5 + 1) + x / 5];
        }
    }

    const basalt::Image<const uint16_t> view(img.ptr, img.w, img.h, img.pitch);
    basalt::KeypointsData kd;
    basalt::detectKeypoints(view, kd, 32, 1);
    basalt::computeAngles(view, kd, true);
    basalt::computeDescriptors(view, kd);

    basalt::VioConfig config;
    config.optical_flow_max_iterations = 7;
    const char* path = "basalt_test_config.json";
    config.save(path);
    basalt::VioConfig loaded;
    loaded.load(path);
    std::remove(path);

    std::cout << "keypoints: " << kd.corners.size() << ", descriptors: " << kd.corner_descriptors.size()
              << ", optical_flow_max_iterations: " << loaded.optical_flow_max_iterations << std::endl;
    return !kd.corners.empty() && kd.corner_descriptors.size() == kd.corners.size() &&
                   loaded.optical_flow_max_iterations == 7
               ? 0
               : 1;
}
