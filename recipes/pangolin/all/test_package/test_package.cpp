#include <pangolin/display/display.h>
#include <pangolin/image/image_io.h>
#include <pangolin/var/var.h>
#include <pangolin/video/video.h>

#include <iostream>
#include <sstream>
#include <vector>

int main()
{
    // No window is created: the test must run on headless machines.
    pangolin::Var<int> frames("ui.frames", 3, 0, 10);

    // The built-in "test" video driver produces synthetic frames.
    auto video = pangolin::OpenVideo("test:[size=64x48,n=1,fmt=GRAY8]//");
    std::vector<unsigned char> buffer(video->SizeBytes());
    int grabbed = 0;
    for (int i = 0; i < frames; ++i) {
        grabbed += video->GrabNext(buffer.data()) ? 1 : 0;
    }

    pangolin::TypedImage image(64, 48, pangolin::PixelFormatFromString("GRAY8"));
    for (size_t y = 0; y < image.h; ++y) {
        for (size_t x = 0; x < image.w; ++x) {
            image.RowPtr(y)[x] = static_cast<unsigned char>(x + y);
        }
    }
#ifdef PANGOLIN_WITH_PNG
    const auto file_type = pangolin::ImageFileTypePng;
#else
    const auto file_type = pangolin::ImageFileTypePpm;
#endif
    std::stringstream encoded;
    pangolin::SaveImage(image, image.fmt, encoded, file_type);
    const pangolin::TypedImage decoded = pangolin::LoadImage(encoded, file_type);

    std::cout << "grabbed " << grabbed << " frames of " << video->SizeBytes() << " bytes; "
              << "encoded " << encoded.str().size() << " bytes, decoded " << decoded.w << "x" << decoded.h << std::endl;
    return grabbed == 3 && decoded.w == 64 && decoded.h == 48 && decoded.RowPtr(10)[20] == 30 ? 0 : 1;
}
