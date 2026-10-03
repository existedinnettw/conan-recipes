#include <deal.II/base/config.h>
#include <deal.II/base/mpi.h>
#include <deal.II/base/utilities.h>
#include <deal.II/dofs/dof_handler.h>
#include <deal.II/fe/fe_q.h>
#include <deal.II/grid/grid_generator.h>
#include <deal.II/grid/grid_tools.h>
#include <deal.II/grid/tria.h>
#include <deal.II/lac/sparsity_tools.h>

#ifdef DEAL_II_WITH_P4EST
#  include <deal.II/distributed/tria.h>
#endif
#ifdef DEAL_II_WITH_PETSC
#  include <deal.II/lac/petsc_vector.h>
#endif
#ifdef DEAL_II_WITH_LAPACK
#  include <deal.II/lac/lapack_full_matrix.h>
#endif

#include <cmath>
#include <iostream>

#ifdef DEAL_II_WITH_MPI
constexpr bool have_mpi = true;
#else
constexpr bool have_mpi = false;
#endif
#ifdef DEAL_II_WITH_P4EST
constexpr bool have_p4est = true;
#else
constexpr bool have_p4est = false;
#endif
#ifdef DEAL_II_WITH_PETSC
constexpr bool have_petsc = true;
#else
constexpr bool have_petsc = false;
#endif
#ifdef DEAL_II_WITH_METIS
constexpr bool have_metis = true;
#else
constexpr bool have_metis = false;
#endif
#ifdef DEAL_II_WITH_LAPACK
constexpr bool have_lapack = true;
#else
constexpr bool have_lapack = false;
#endif
#ifdef DEAL_II_WITH_ZLIB
constexpr bool have_zlib = true;
#else
constexpr bool have_zlib = false;
#endif
#ifdef DEAL_II_WITH_COMPLEX_VALUES
constexpr bool have_complex = true;
#else
constexpr bool have_complex = false;
#endif
#ifdef DEAL_II_WITH_64BIT_INDICES
constexpr bool have_64bit = true;
#else
constexpr bool have_64bit = false;
#endif

static_assert(have_mpi == EXPECT_MPI, "DEAL_II_WITH_MPI does not match option with_mpi");
static_assert(have_p4est == EXPECT_P4EST, "DEAL_II_WITH_P4EST does not match option with_p4est");
static_assert(have_petsc == EXPECT_PETSC, "DEAL_II_WITH_PETSC does not match option with_petsc");
static_assert(have_metis == EXPECT_METIS, "DEAL_II_WITH_METIS does not match option with_metis");
static_assert(have_lapack == EXPECT_LAPACK, "DEAL_II_WITH_LAPACK does not match option with_lapack");
static_assert(have_zlib == EXPECT_ZLIB, "DEAL_II_WITH_ZLIB does not match option with_zlib");
static_assert(have_complex == EXPECT_COMPLEX_VALUES, "DEAL_II_WITH_COMPLEX_VALUES does not match option with_complex_values");
static_assert(have_64bit == EXPECT_64BIT_INDICES, "DEAL_II_WITH_64BIT_INDICES does not match option int64");

using namespace dealii;

int main(int argc, char *argv[])
{
  Utilities::MPI::MPI_InitFinalize mpi(argc, argv, 1);
  const MPI_Comm comm = MPI_COMM_WORLD;
  const bool root = Utilities::MPI::this_mpi_process(comm) == 0;
  if (root)
    std::cout << "deal.II " << DEAL_II_PACKAGE_VERSION << " on "
              << Utilities::MPI::n_mpi_processes(comm) << " rank(s)\n";

  // A unit square refined four times: 256 cells, 289 Q1 unknowns.
#ifdef DEAL_II_WITH_P4EST
  parallel::distributed::Triangulation<2> tria(comm);
#else
  Triangulation<2> tria;
#endif
  GridGenerator::hyper_cube(tria);
  tria.refine_global(4);

  DoFHandler<2> dof_handler(tria);
  const FE_Q<2> fe(1);
  dof_handler.distribute_dofs(fe);

  const auto n_cells = tria.n_global_active_cells();
  const auto n_dofs = dof_handler.n_dofs();
  if (root)
    std::cout << "cells: " << n_cells << ", dofs: " << n_dofs << "\n";
  AssertThrow(n_cells == 256 && n_dofs == 289, ExcInternalError());

#ifdef DEAL_II_WITH_PETSC
  {
    // A distributed PETSc vector of ones; its l1 norm is the global size.
    PETScWrappers::MPI::Vector v(dof_handler.locally_owned_dofs(), comm);
    v = 1.0;
    const double norm = v.l1_norm();
    if (root)
      std::cout << "PETSc vector l1 norm: " << norm << "\n";
    AssertThrow(std::abs(norm - n_dofs) < 1e-12, ExcInternalError());
  }
#endif

#ifdef DEAL_II_WITH_LAPACK
  {
    // Invert diag(2, 4) through LAPACK.
    LAPACKFullMatrix<double> m(2, 2);
    m(0, 0) = 2.0;
    m(1, 1) = 4.0;
    m.invert();
    AssertThrow(std::abs(m(0, 0) - 0.5) < 1e-14 && std::abs(m(1, 1) - 0.25) < 1e-14,
                ExcInternalError());
    if (root)
      std::cout << "LAPACK inverse: " << m(0, 0) << ", " << m(1, 1) << "\n";
  }
#endif

#ifdef DEAL_II_WITH_METIS
  {
    // Partition a serial mesh into four subdomains with METIS.
    Triangulation<2> serial;
    GridGenerator::hyper_cube(serial);
    serial.refine_global(3);
    GridTools::partition_triangulation(4, serial, SparsityTools::Partitioner::metis);
    std::vector<unsigned int> per_part(4, 0);
    for (const auto &cell : serial.active_cell_iterators())
      ++per_part[cell->subdomain_id()];
    if (root)
      std::cout << "METIS parts: " << per_part[0] << " " << per_part[1] << " "
                << per_part[2] << " " << per_part[3] << "\n";
    for (const auto n : per_part)
      AssertThrow(n > 0, ExcInternalError());
  }
#endif

  return 0;
}
