#include <cstdlib>
#include <iostream>
#include <random>
#include <vector>

#include <nlf/UKF.h>
#include "DragBallModel.h"
#include "rbpf/resampling.hpp"

int main() {
    // Header-only UKF over the bundled drag-ball model; FilterMath.h pulls in the
    // OptMathKernels headers.
    DragBallModel model;
    UKFCore::UKF<4, 2> ukf(model);

    DragBallModel::State x0;
    x0 << 0.0f, 100.0f, 10.0f, 0.0f;
    ukf.initialize(x0, DragBallModel::StateMat::Identity());
    ukf.predict(0.0f, DragBallModel::State::Zero());
    ukf.update(0.1f, model.h(x0, 0.1f));

    // Compiled code in the rbpf_core library.
    std::mt19937_64 rng(42);
    const std::vector<int> parents = rbpf::systematic_resampling({0.25f, 0.25f, 0.5f}, rng);

    std::cout << "UKF x = " << ukf.getState().transpose() << "\n"
              << "resampled " << parents.size() << " particles\n";
    return parents.size() == 3 ? EXIT_SUCCESS : EXIT_FAILURE;
}
