#include <aruco_nano.h>

#include <iostream>

int main()
{
  cv::Mat image(240, 320, CV_8UC3, cv::Scalar(255, 255, 255));
  const auto markers = aruco_nano::MarkerDetector::detect(image);
  std::cout << "aruco_nano detected " << markers.size() << " markers on a blank image" << std::endl;
  return markers.empty() ? 0 : 1;
}
