// Opens the mesh of the test case and checks its cell count and volume, summed over
// all processors when run with -parallel.

#include "argList.H"
#include "Time.H"
#include "fvMesh.H"
#include "volMesh.H"
#include "columnFvMesh.H"  // for the -dry-run branch of createMesh.H

using namespace Foam;

int main(int argc, char *argv[])
{
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"

    const label nCells = returnReduce(mesh.nCells(), sumOp<label>());
    const scalar volume = gSum(static_cast<const scalarField&>(mesh.V()));

    Info<< "cells: " << nCells << ", volume: " << volume
        << ", processors: " << Pstream::nProcs() << endl;

    return (nCells == 100 && mag(volume - 0.1) < 1e-9) ? 0 : 1;
}
