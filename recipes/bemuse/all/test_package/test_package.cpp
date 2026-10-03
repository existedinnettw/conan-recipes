// Radiation problem of a sphere (radius 1, centre 3 below the free surface) at one
// frequency, through the library API. The solver writes its results under Output/
// relative to the working directory.
#include "Boundary/Ellipsoid.h"
#include "Solver/Hydrodynamic_Solver.h"

#include <fstream>
#include <iostream>

int main()
{
    std::vector<Real> dimensions = {1.0, 1.0, 1.0, 3.0};   // semi-axes a, b, c; depth
    std::vector<int> discretisation = {12, 8};              // azimuthal, zenith panels

    BEMUse::Ellipsoid sphere;
    sphere.Set_Dimensions(dimensions);
    sphere.Set_Discretisation(discretisation);
    sphere.Setup();

    BEMUse::Hydrodynamic_Radiation_Solver solver;
    std::string prefix = "sphere";
    solver.Set_OutputFilePath(prefix);
    solver.Setup(&sphere);
    solver.Set_Real(1.0);
    solver.Solve();

    std::ifstream result("Output/sphere.1");
    if (!result) {
        std::cerr << "no Output/sphere.1 written\n";
        return 1;
    }
    std::string line;
    int lines = 0;
    while (std::getline(result, line)) ++lines;
    std::cout << "Output/sphere.1: " << lines << " lines\n";
    return lines > 0 ? 0 : 1;
}
