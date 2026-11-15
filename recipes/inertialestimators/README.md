# InertialEstimators

Packages the six C++ estimators from Tellicious/InertialEstimators v3.1.0.
The C implementations are not included: they depend on ADV-utils and an
application-provided `main.h` for embedded configuration. C and C++ also ship
headers with the same names.

```ini
[requires]
inertialestimators/3.1.0

[generators]
CMakeDeps
CMakeToolchain
```

```cmake
find_package(inertialestimators REQUIRED CONFIG)
target_link_libraries(app PRIVATE inertialestimators::inertialestimators)
```

```cpp
#include <AHRS_Attitude_SO3.h>

// Mahony-based SO(3) complementary filter: timestep in seconds, Kp, Ki.
AHRS_Attitude_SO3 filter(0.01f, 1.0f, 0.05f);
// Feed gyro (rad/s), acceleration and magnetic field in upstream's body frame.
filter.compute(gx, gy, gz, ax, ay, az, mx, my, mz);
```

Upstream uses X forward, Y right, Z down; Euler outputs are radians.
`InertialEstimator.h` includes all estimators. MatLib is a transitive dependency.
Static and shared builds are supported. The recipe patches invalid `1f`/`0f`
literals without changing the estimator algorithms.
