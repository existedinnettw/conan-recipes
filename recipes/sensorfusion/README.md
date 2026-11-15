# SensorFusion

Packages [Library-SensorFusion](https://github.com/martinbudden/Library-SensorFusion)
0.2.14, with ComplementaryFilter, MahonyFilter, MadgwickFilter, BasicVQF and VQF.
Requires C++20. VectorQuaternionMatrix 0.4.10 is a public dependency.

```ini
[requires]
sensorfusion/0.2.14

[generators]
CMakeDeps
CMakeToolchain
```

```cmake
find_package(sensorfusion REQUIRED CONFIG)
target_link_libraries(app PRIVATE sensorfusion::sensorfusion)
```

```cpp
#include <SensorFusion.h>

MahonyFilter filter;
filter.setKpKi(1.0f, 0.0f);
// Gyroscope in radians/second, acceleration in g, timestep in seconds.
auto orientation = filter.updateOrientation(
    xyz_t{0.f, 0.f, 0.1f}, xyz_t{0.f, 0.f, 1.f}, 0.01f);
```

Header and method names follow the tagged release (`SensorFusion.h`,
`updateOrientation`), which differs from upstream main's snake_case API.
The recipe makes the release's private MahonyFilter constructors public.
It builds the library without the PlatformIO demonstration main.cpp, supports
static/shared builds, and retains upstream's default feature macros.

Upstream limitations in 0.2.14: Mahony's magnetometer overload ignores the
magnetometer. Its optional matrix exponential integration produces NaNs at
zero corrected gyro rate; the default Euler integration avoids that path.
Madgwick's correction also has a singularity when the correction gradient is
zero. This recipe preserves the upstream filter algorithms.
