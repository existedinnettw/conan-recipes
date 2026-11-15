// Renders a depth-2 RArUco marker on a white page and detects it back.
#include <opencv2/objdetect/aruco2.hpp>
#include <opencv2/imgproc.hpp>

#include <cstdio>

int main()
{
    cv::Mat marker;
    cv::aruco2::getRArucoMarkerImage(marker, cv::aruco2::DICT_APRILTAG_16h5, 3, 2, 4, 2, true);
    cv::Mat page(marker.rows + 80, marker.cols + 80, CV_8UC1, cv::Scalar(255));
    marker.copyTo(page(cv::Rect(40, 40, marker.cols, marker.rows)));
    const auto found = cv::aruco2::detectRArucoMarkers(page, cv::aruco2::DICT_APRILTAG_16h5);
    int outer = 0;
    for (const auto& m : found)
    {
        outer += m.id == 3;
    }
    std::printf("aruco2: %zu RArUco markers detected in a %dx%d page\n", found.size(), page.cols, page.rows);
    return outer > 0 ? 0 : 1;
}
