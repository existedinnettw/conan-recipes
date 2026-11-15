#include <MatLib.h>
#include <cmath>

int main() {
    MatrixXf matrix(2, 2);
    matrix = {2.f, 0.f, 0.f, 4.f};
    MatrixXf inverse = !matrix;
    MatrixXf product = matrix * inverse;
    return std::fabs(product.get(0, 0) - 1.f) < 1e-5f &&
           std::fabs(product.get(1, 1) - 1.f) < 1e-5f ? 0 : 1;
}
