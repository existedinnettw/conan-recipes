#include <stdio.h>

#include <HYPRE.h>
#include <HYPRE_IJ_mv.h>
/* Installed internal header; it is what defines MPI_COMM_WORLD for serial builds. */
#include <_hypre_utilities.h>

#ifdef HYPRE_HAVE_MPI
#define HAVE_MPI 1
#include <mpi.h>
#else
#define HAVE_MPI 0
#endif

#ifdef HYPRE_BIGINT
#define HAVE_BIGINT 1
#else
#define HAVE_BIGINT 0
#endif

/* The options must match what hypre actually compiled in. */
_Static_assert(HAVE_MPI == EXPECT_MPI, "HYPRE_HAVE_MPI does not match option with_mpi");
_Static_assert(HAVE_BIGINT == EXPECT_BIGINT, "HYPRE_BIGINT does not match option bigint");

int main(int argc, char **argv)
{
#if HAVE_MPI
   MPI_Init(&argc, &argv);
#else
   (void)argc;
   (void)argv;
#endif

   HYPRE_Init();

   /* Build a small 4x4 identity matrix through the IJ interface. */
   HYPRE_IJMatrix A;
   HYPRE_IJMatrixCreate(MPI_COMM_WORLD, 0, 3, 0, 3, &A);
   HYPRE_IJMatrixSetObjectType(A, HYPRE_PARCSR);
   HYPRE_IJMatrixInitialize(A);

   for (HYPRE_BigInt row = 0; row < 4; row++)
   {
      HYPRE_Int ncols = 1;
      HYPRE_Complex value = 1.0;
      HYPRE_IJMatrixSetValues(A, 1, &ncols, &row, &row, &value);
   }

   HYPRE_IJMatrixAssemble(A);

   printf("hypre %s\n", HYPRE_RELEASE_VERSION);
   printf("sizeof(HYPRE_BigInt): %d\n", (int)sizeof(HYPRE_BigInt));

   HYPRE_IJMatrixDestroy(A);
   HYPRE_Finalize();

#if HAVE_MPI
   MPI_Finalize();
#endif

   return 0;
}
