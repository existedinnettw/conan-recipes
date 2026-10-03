#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include <superlu_ddefs.h>

/* Solves the 1D Poisson matrix tridiag(-1, 2, -1) of order n with the
 * replicated-input driver pdgssvx_ABglobal on a 1 x 1 process grid. */
int main(int argc, char *argv[])
{
    MPI_Init(&argc, &argv);

    const int_t n = 10;
    const int_t nnz = 3 * n - 2;
    double *a = doubleMalloc_dist(nnz);
    int_t *asub = intMalloc_dist(nnz);
    int_t *xa = intMalloc_dist(n + 1);

    /* Compressed column storage. */
    int_t k = 0;
    for (int_t j = 0; j < n; ++j) {
        xa[j] = k;
        if (j > 0) { asub[k] = j - 1; a[k++] = -1.0; }
        asub[k] = j; a[k++] = 2.0;
        if (j < n - 1) { asub[k] = j + 1; a[k++] = -1.0; }
    }
    xa[n] = k;

    SuperMatrix A;
    dCreate_CompCol_Matrix_dist(&A, n, n, nnz, a, asub, xa, SLU_NC, SLU_D, SLU_GE);

    /* Right-hand side for the solution x = 1: b = A * 1. */
    double *b = doubleMalloc_dist(n);
    for (int_t i = 0; i < n; ++i)
        b[i] = (i == 0 || i == n - 1) ? 1.0 : 0.0;

    gridinfo_t grid;
    superlu_gridinit(MPI_COMM_WORLD, 1, 1, &grid);

    superlu_dist_options_t options;
    set_default_options_dist(&options);
    options.PrintStat = NO;

    dScalePermstruct_t ScalePermstruct;
    dLUstruct_t LUstruct;
    SuperLUStat_t stat;
    dScalePermstructInit(n, n, &ScalePermstruct);
    dLUstructInit(n, &LUstruct);
    PStatInit(&stat);

    /* Ranks beyond the 1 x 1 grid (when run with mpirun -np > 1) only idle. */
    const int in_grid = grid.iam < grid.nprow * grid.npcol;
    double berr[1];
    int info = 0;
    double err = 0.0;
    if (in_grid) {
        pdgssvx_ABglobal(&options, &A, &ScalePermstruct, b, n, 1, &grid, &LUstruct, berr,
                         &stat, &info);
        for (int_t i = 0; i < n; ++i)
            err = fmax(err, fabs(b[i] - 1.0));
    }
    if (grid.iam == 0)
        printf("SuperLU_DIST %d.%d.%d: info %d, max error %g (int_t: %d bits)\n",
               SUPERLU_DIST_MAJOR_VERSION, SUPERLU_DIST_MINOR_VERSION,
               SUPERLU_DIST_PATCH_VERSION, info, err, (int)(8 * sizeof(int_t)));

    PStatFree(&stat);
    Destroy_CompCol_Matrix_dist(&A);
    if (in_grid)
        dDestroy_LU(n, &grid, &LUstruct);
    dScalePermstructFree(&ScalePermstruct);
    dLUstructFree(&LUstruct);
    SUPERLU_FREE(b);
    superlu_gridexit(&grid);
    MPI_Finalize();
    return info == 0 && err < 1e-10 ? EXIT_SUCCESS : EXIT_FAILURE;
}
