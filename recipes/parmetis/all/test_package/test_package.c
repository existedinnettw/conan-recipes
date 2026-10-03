#include <stdio.h>
#include <stdlib.h>

#include <mpi.h>
#include <parmetis.h>

/* Partitions a 16-vertex ring into 4 parts, the graph spread over all ranks. */
int main(int argc, char *argv[])
{
    MPI_Init(&argc, &argv);
    MPI_Comm comm = MPI_COMM_WORLD;
    int rank, size;
    MPI_Comm_rank(comm, &rank);
    MPI_Comm_size(comm, &size);

    const idx_t nvtxs = 16;
    idx_t *vtxdist = malloc((size + 1) * sizeof(idx_t));
    for (int p = 0; p <= size; ++p)
        vtxdist[p] = (nvtxs * p) / size;

    const idx_t first = vtxdist[rank];
    const idx_t nlocal = vtxdist[rank + 1] - first;
    idx_t *xadj = malloc((nlocal + 1) * sizeof(idx_t));
    idx_t *adjncy = malloc(2 * nlocal * sizeof(idx_t));
    for (idx_t i = 0; i < nlocal; ++i) {
        const idx_t v = first + i;
        xadj[i] = 2 * i;
        adjncy[2 * i] = (v + nvtxs - 1) % nvtxs;
        adjncy[2 * i + 1] = (v + 1) % nvtxs;
    }
    xadj[nlocal] = 2 * nlocal;

    idx_t wgtflag = 0, numflag = 0, ncon = 1, nparts = 4, edgecut = 0;
    idx_t options[3] = {0, 0, 0};
    real_t tpwgts[4] = {0.25, 0.25, 0.25, 0.25};
    real_t ubvec[1] = {1.05};
    idx_t *part = malloc(nlocal * sizeof(idx_t));

    const int status = ParMETIS_V3_PartKway(vtxdist, xadj, adjncy, NULL, NULL, &wgtflag,
                                            &numflag, &ncon, &nparts, tpwgts, ubvec,
                                            options, &edgecut, part, &comm);
    if (rank == 0)
        printf("ParMETIS %d.%d.%d: status %d, edge cut %ld (ranks: %d, idx_t: %d bits)\n",
               PARMETIS_MAJOR_VERSION, PARMETIS_MINOR_VERSION, PARMETIS_SUBMINOR_VERSION,
               status, (long)edgecut, size, (int)(8 * sizeof(idx_t)));

    free(part);
    free(adjncy);
    free(xadj);
    free(vtxdist);
    MPI_Finalize();
    return status == METIS_OK && edgecut > 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
