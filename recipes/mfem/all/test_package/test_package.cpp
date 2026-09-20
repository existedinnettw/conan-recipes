#include <iostream>
#include <memory>

#include "mfem.hpp"

#ifdef MFEM_USE_MPI
#define HAVE_MPI 1
#else
#define HAVE_MPI 0
#endif

#ifdef MFEM_USE_METIS
#define HAVE_METIS 1
#else
#define HAVE_METIS 0
#endif

#ifdef MFEM_USE_ZLIB
#define HAVE_ZLIB 1
#else
#define HAVE_ZLIB 0
#endif

#ifdef MFEM_USE_LAPACK
#define HAVE_LAPACK 1
#else
#define HAVE_LAPACK 0
#endif

#ifdef MFEM_USE_OPENMP
#define HAVE_OPENMP 1
#else
#define HAVE_OPENMP 0
#endif

static_assert(HAVE_MPI == EXPECT_MPI, "MFEM_USE_MPI does not match option with_mpi");
static_assert(HAVE_METIS == EXPECT_MPI, "MFEM_USE_METIS does not match option with_mpi");
static_assert(HAVE_ZLIB == EXPECT_ZLIB, "MFEM_USE_ZLIB does not match option with_zlib");
static_assert(HAVE_LAPACK == EXPECT_LAPACK, "MFEM_USE_LAPACK does not match option with_lapack");
static_assert(HAVE_OPENMP == EXPECT_OPENMP, "MFEM_USE_OPENMP does not match option with_openmp");

#if HAVE_MPI
// The parallel build must agree with hypre on the scalar type, and MFEM_USE_METIS_5
// has to match the METIS package: both are set by hand in the recipe rather than
// detected by MFEM's own find modules.
static_assert(sizeof(mfem::real_t) == sizeof(HYPRE_Real),
              "mfem::real_t and HYPRE_Real disagree");
#endif

int main(int argc, char *argv[])
{
#if HAVE_MPI
   mfem::Mpi::Init(argc, argv);
   mfem::Hypre::Init();
#else
   (void)argc;
   (void)argv;
#endif

   // A 2x2 quadrilateral mesh on the unit square, refined once.
   mfem::Mesh mesh = mfem::Mesh::MakeCartesian2D(2, 2, mfem::Element::QUADRILATERAL);
   mesh.UniformRefinement();

   mfem::H1_FECollection fec(1, mesh.Dimension());

#if HAVE_MPI
   // ParMesh partitions the serial mesh with METIS, and the assembled operator is a
   // hypre ParCSR matrix, so this exercises both parallel dependencies.
   mfem::ParMesh pmesh(MPI_COMM_WORLD, mesh);
   mfem::ParFiniteElementSpace fespace(&pmesh, &fec);

   mfem::ParBilinearForm mass(&fespace);
   mass.AddDomainIntegrator(new mfem::MassIntegrator);
   mass.Assemble();
   mass.Finalize();
   std::unique_ptr<mfem::HypreParMatrix> M(mass.ParallelAssemble());

   if (mfem::Mpi::Root())
   {
      std::cout << "MFEM " << MFEM_VERSION_STRING << " (parallel)\n";
      std::cout << "ranks: " << mfem::Mpi::WorldSize() << "\n";
      std::cout << "unknowns: " << fespace.GlobalTrueVSize() << "\n";
      std::cout << "mass matrix rows: " << M->GetGlobalNumRows() << "\n";
   }
#else
   mfem::FiniteElementSpace fespace(&mesh, &fec);

   // Assemble a mass matrix, which exercises the quadrature and sparse assembly.
   mfem::BilinearForm mass(&fespace);
   mass.AddDomainIntegrator(new mfem::MassIntegrator);
   mass.Assemble();
   mass.Finalize();

   std::cout << "MFEM " << MFEM_VERSION_STRING << " (serial)\n";
   std::cout << "elements: " << mesh.GetNE() << "\n";
   std::cout << "unknowns: " << fespace.GetTrueVSize() << "\n";
   std::cout << "mass matrix nnz: " << mass.SpMat().NumNonZeroElems() << "\n";
#endif

   return 0;
}
