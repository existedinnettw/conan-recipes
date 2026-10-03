#include <stdlib.h>

#include <p4est_extended.h>
#if TEST_P8EST
#include <p8est_extended.h>
#endif

#ifdef P4EST_ENABLE_MPI
#define HAVE_MPI 1
#else
#define HAVE_MPI 0
#endif
_Static_assert(HAVE_MPI == EXPECT_MPI, "P4EST_ENABLE_MPI does not match option with_mpi");

/* Refines a forest uniformly to the given level, partitions it over all ranks and
 * checks the global number of quadrants (octants in 3D). */
int main(int argc, char **argv)
{
    sc_MPI_Comm comm = sc_MPI_COMM_WORLD;
    int mpiret = sc_MPI_Init(&argc, &argv);
    SC_CHECK_MPI(mpiret);
    sc_init(comm, 1, 1, NULL, SC_LP_ESSENTIAL);
    p4est_init(NULL, SC_LP_PRODUCTION);

    const int level = 3;
    int ok = 1;

    p4est_connectivity_t *conn = p4est_connectivity_new_brick(2, 1, 0, 0);
    p4est_t *p4est = p4est_new_ext(comm, conn, 0, level, 1, 0, NULL, NULL);
    p4est_partition(p4est, 0, NULL);
    const p4est_gloidx_t expected = 2 * (1 << (2 * level));
    ok = ok && p4est->global_num_quadrants == expected;
    P4EST_GLOBAL_PRODUCTIONF("p4est %s: %lld quadrants in 2D (expected %lld), %d rank(s)\n",
                             p4est_version(), (long long)p4est->global_num_quadrants,
                             (long long)expected, p4est->mpisize);
    p4est_destroy(p4est);
    p4est_connectivity_destroy(conn);

#if TEST_P8EST
    p8est_connectivity_t *conn3 = p8est_connectivity_new_unitcube();
    p8est_t *p8est = p8est_new_ext(comm, conn3, 0, level, 1, 0, NULL, NULL);
    p8est_partition(p8est, 0, NULL);
    const p4est_gloidx_t expected3 = (p4est_gloidx_t)1 << (3 * level);
    ok = ok && p8est->global_num_quadrants == expected3;
    P4EST_GLOBAL_PRODUCTIONF("p8est: %lld octants in 3D (expected %lld)\n",
                             (long long)p8est->global_num_quadrants, (long long)expected3);
    p8est_destroy(p8est);
    p8est_connectivity_destroy(conn3);
#endif

    sc_finalize();
    mpiret = sc_MPI_Finalize();
    SC_CHECK_MPI(mpiret);
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
