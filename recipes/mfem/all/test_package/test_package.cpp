#include <iostream>

#include "mfem.hpp"

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

static_assert(HAVE_ZLIB == EXPECT_ZLIB, "MFEM_USE_ZLIB does not match option with_zlib");
static_assert(HAVE_LAPACK == EXPECT_LAPACK, "MFEM_USE_LAPACK does not match option with_lapack");
static_assert(HAVE_OPENMP == EXPECT_OPENMP, "MFEM_USE_OPENMP does not match option with_openmp");

int main()
{
   // A 2x2 quadrilateral mesh on the unit square, refined once.
   mfem::Mesh mesh = mfem::Mesh::MakeCartesian2D(2, 2, mfem::Element::QUADRILATERAL);
   mesh.UniformRefinement();

   mfem::H1_FECollection fec(1, mesh.Dimension());
   mfem::FiniteElementSpace fespace(&mesh, &fec);

   // Assemble a mass matrix, which exercises the quadrature and sparse assembly.
   mfem::BilinearForm mass(&fespace);
   mass.AddDomainIntegrator(new mfem::MassIntegrator);
   mass.Assemble();
   mass.Finalize();

   std::cout << "MFEM " << MFEM_VERSION_STRING << "\n";
   std::cout << "elements: " << mesh.GetNE() << "\n";
   std::cout << "unknowns: " << fespace.GetTrueVSize() << "\n";
   std::cout << "mass matrix nnz: " << mass.SpMat().NumNonZeroElems() << "\n";

   return 0;
}
