#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#ifdef WITH_PTSCOTCH
#include <mpi.h>
#include <ptscotch.h>
#else
#include <scotch.h>
#endif

/* Partition a 6-vertex ring into two parts of three vertices each. */
static int partition_ring(void)
{
    SCOTCH_Num verttab[] = {0, 2, 4, 6, 8, 10, 12};
    SCOTCH_Num edgetab[] = {1, 5, 0, 2, 1, 3, 2, 4, 3, 5, 4, 0};
    SCOTCH_Num parttab[6];
    SCOTCH_Graph graph;
    SCOTCH_Strat strat;
    int sizes[2] = {0, 0};
    int i;

    if (SCOTCH_graphInit(&graph) != 0
        || SCOTCH_graphBuild(&graph, 0, 6, verttab, NULL, NULL, NULL, 12, edgetab, NULL) != 0
        || SCOTCH_graphCheck(&graph) != 0) {
        fprintf(stderr, "failed to build graph\n");
        return 1;
    }
    SCOTCH_stratInit(&strat);
    if (SCOTCH_graphPart(&graph, 2, &strat, parttab) != 0) {
        fprintf(stderr, "SCOTCH_graphPart failed\n");
        return 1;
    }
    SCOTCH_stratExit(&strat);
    SCOTCH_graphExit(&graph);

    for (i = 0; i < 6; ++i)
        sizes[parttab[i]]++;
    printf("scotch %d.%d.%d: ring of 6 split into %d + %d\n",
           SCOTCH_VERSION, SCOTCH_RELEASE, SCOTCH_PATCHLEVEL, sizes[0], sizes[1]);
    return (sizes[0] == 3 && sizes[1] == 3) ? 0 : 1;
}

int main(int argc, char **argv)
{
    int status = partition_ring();
#ifdef WITH_PTSCOTCH
    SCOTCH_Dgraph dgraph;
    MPI_Init(&argc, &argv);
    if (SCOTCH_dgraphInit(&dgraph, MPI_COMM_WORLD) != 0) {
        fprintf(stderr, "SCOTCH_dgraphInit failed\n");
        status = 1;
    } else {
        SCOTCH_dgraphExit(&dgraph);
        printf("ptscotch: distributed graph initialised\n");
    }
    MPI_Finalize();
#else
    (void)argc;
    (void)argv;
#endif
    return status;
}
