#include <string.h>

#include <petscksp.h>
#include <petscmat.h>

#if defined(PETSC_HAVE_MPIUNI)
#define HAVE_MPI 0
#else
#define HAVE_MPI 1
#endif
#if defined(PETSC_HAVE_HYPRE)
#define HAVE_HYPRE 1
#else
#define HAVE_HYPRE 0
#endif
#if defined(PETSC_HAVE_METIS)
#define HAVE_METIS 1
#else
#define HAVE_METIS 0
#endif
#if defined(PETSC_HAVE_PARMETIS)
#define HAVE_PARMETIS 1
#else
#define HAVE_PARMETIS 0
#endif
#if defined(PETSC_HAVE_PTSCOTCH)
#define HAVE_PTSCOTCH 1
#else
#define HAVE_PTSCOTCH 0
#endif
#if defined(PETSC_HAVE_SUPERLU_DIST)
#define HAVE_SUPERLU_DIST 1
#else
#define HAVE_SUPERLU_DIST 0
#endif
#if defined(PETSC_HAVE_HDF5)
#define HAVE_HDF5 1
#else
#define HAVE_HDF5 0
#endif
#if defined(PETSC_USE_64BIT_INDICES)
#define HAVE_INT64 1
#else
#define HAVE_INT64 0
#endif
#if defined(PETSC_USE_COMPLEX)
#define HAVE_COMPLEX 1
#else
#define HAVE_COMPLEX 0
#endif

_Static_assert(HAVE_MPI == EXPECT_MPI, "MPI does not match option with_mpi");
_Static_assert(HAVE_HYPRE == EXPECT_HYPRE, "PETSC_HAVE_HYPRE does not match option with_hypre");
_Static_assert(HAVE_METIS == EXPECT_METIS, "PETSC_HAVE_METIS does not match option with_metis");
_Static_assert(HAVE_PARMETIS == EXPECT_PARMETIS, "PETSC_HAVE_PARMETIS does not match option with_parmetis");
_Static_assert(HAVE_PTSCOTCH == EXPECT_PTSCOTCH, "PETSC_HAVE_PTSCOTCH does not match option with_ptscotch");
_Static_assert(HAVE_SUPERLU_DIST == EXPECT_SUPERLU_DIST, "PETSC_HAVE_SUPERLU_DIST does not match option with_superlu_dist");
_Static_assert(HAVE_HDF5 == EXPECT_HDF5, "PETSC_HAVE_HDF5 does not match option with_hdf5");
_Static_assert(HAVE_INT64 == EXPECT_INT64, "PETSC_USE_64BIT_INDICES does not match option int64");
_Static_assert(HAVE_COMPLEX == EXPECT_COMPLEX, "PETSC_USE_COMPLEX does not match option scalar_type");

/* Solves the 1D Poisson problem tridiag(-1, 2, -1) x = A * 1 with the given
 * preconditioner and checks that x = 1 comes back. */
static PetscErrorCode Solve(Mat A, Vec b, Vec x, Vec ones, PCType pctype, MatSolverType solver)
{
  KSP       ksp;
  PC        pc;
  PetscReal err;
  PetscInt  its;

  PetscFunctionBeginUser;
  PetscCall(KSPCreate(PETSC_COMM_WORLD, &ksp));
  PetscCall(KSPSetOperators(ksp, A, A));
  /* The matrix is symmetric positive definite. */
  PetscCall(KSPSetType(ksp, KSPCG));
  PetscCall(KSPSetTolerances(ksp, 1e-10, PETSC_CURRENT, PETSC_CURRENT, 500));
  PetscCall(KSPGetPC(ksp, &pc));
  PetscCall(PCSetType(pc, pctype));
  if (solver) {
    PetscCall(KSPSetType(ksp, KSPPREONLY));
    PetscCall(PCFactorSetMatSolverType(pc, solver));
  }
  PetscCall(VecZeroEntries(x));
  PetscCall(KSPSolve(ksp, b, x));
  PetscCall(KSPGetIterationNumber(ksp, &its));
  PetscCall(VecAXPY(x, -1.0, ones));
  PetscCall(VecNorm(x, NORM_INFINITY, &err));
  PetscCall(PetscPrintf(PETSC_COMM_WORLD, "%-24s %3" PetscInt_FMT " iterations, error %g\n", solver ? solver : pctype, its, (double)err));
  PetscCheck(err < 1e-6, PETSC_COMM_WORLD, PETSC_ERR_PLIB, "%s did not solve the system", solver ? solver : pctype);
  PetscCall(KSPDestroy(&ksp));
  PetscFunctionReturn(PETSC_SUCCESS);
}

int main(int argc, char **argv)
{
  Mat         A;
  Vec         x, b, ones;
  PetscInt    n = 100, start, end;
  PetscMPIInt size;

  PetscCall(PetscInitialize(&argc, &argv, NULL, NULL));
  PetscCallMPI(MPI_Comm_size(PETSC_COMM_WORLD, &size));
  PetscCall(PetscPrintf(PETSC_COMM_WORLD, "PETSc %d.%d.%d on %d rank(s), sizeof(PetscInt) = %d\n", PETSC_VERSION_MAJOR, PETSC_VERSION_MINOR, PETSC_VERSION_SUBMINOR, size, (int)sizeof(PetscInt)));

  /* zlib gets no PETSC_HAVE_ macro of its own, only an entry in the package list. */
  PetscCheck((strstr(PETSC_HAVE_PACKAGES, ":zlib:") != NULL) == EXPECT_ZLIB, PETSC_COMM_WORLD, PETSC_ERR_PLIB, "zlib in PETSC_HAVE_PACKAGES does not match option with_zlib");

  PetscCall(MatCreateAIJ(PETSC_COMM_WORLD, PETSC_DECIDE, PETSC_DECIDE, n, n, 3, NULL, 1, NULL, &A));
  PetscCall(MatGetOwnershipRange(A, &start, &end));
  for (PetscInt i = start; i < end; ++i) {
    if (i > 0) PetscCall(MatSetValue(A, i, i - 1, -1.0, INSERT_VALUES));
    PetscCall(MatSetValue(A, i, i, 2.0, INSERT_VALUES));
    if (i < n - 1) PetscCall(MatSetValue(A, i, i + 1, -1.0, INSERT_VALUES));
  }
  PetscCall(MatAssemblyBegin(A, MAT_FINAL_ASSEMBLY));
  PetscCall(MatAssemblyEnd(A, MAT_FINAL_ASSEMBLY));

  PetscCall(MatCreateVecs(A, &x, &b));
  PetscCall(VecDuplicate(x, &ones));
  PetscCall(VecSet(ones, 1.0));
  PetscCall(MatMult(A, ones, b));

  PetscCall(Solve(A, b, x, ones, PCJACOBI, NULL));
#if HAVE_HYPRE
  PetscCall(Solve(A, b, x, ones, PCHYPRE, NULL));
#endif
#if HAVE_SUPERLU_DIST
  PetscCall(Solve(A, b, x, ones, PCLU, MATSOLVERSUPERLU_DIST));
#endif

#if HAVE_PARMETIS || HAVE_PTSCOTCH
  {
    /* Partition the matrix graph into as many parts as there are ranks. */
    MatPartitioning part;
    IS              is;
    PetscCall(MatPartitioningCreate(PETSC_COMM_WORLD, &part));
    PetscCall(MatPartitioningSetAdjacency(part, A));
  #if HAVE_PARMETIS
    PetscCall(MatPartitioningSetType(part, MATPARTITIONINGPARMETIS));
  #else
    PetscCall(MatPartitioningSetType(part, MATPARTITIONINGPTSCOTCH));
  #endif
    PetscCall(MatPartitioningApply(part, &is));
    PetscCall(PetscPrintf(PETSC_COMM_WORLD, "partitioned with %s\n", HAVE_PARMETIS ? "ParMETIS" : "PT-Scotch"));
    PetscCall(ISDestroy(&is));
    PetscCall(MatPartitioningDestroy(&part));
  }
#endif

  PetscCall(VecDestroy(&ones));
  PetscCall(VecDestroy(&b));
  PetscCall(VecDestroy(&x));
  PetscCall(MatDestroy(&A));
  PetscCall(PetscFinalize());
  return 0;
}
