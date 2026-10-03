#include <AMReX.H>
#include <AMReX_MultiFab.H>
#include <AMReX_Print.H>

#if EXPECT_LINEAR_SOLVERS
#include <AMReX_MLMG.H>
#include <AMReX_MLPoisson.H>
#endif

#ifdef AMREX_USE_MPI
#define HAVE_MPI 1
#else
#define HAVE_MPI 0
#endif

#ifdef AMREX_USE_OMP
#define HAVE_OPENMP 1
#else
#define HAVE_OPENMP 0
#endif

#ifdef AMREX_USE_EB
#define HAVE_EB 1
#else
#define HAVE_EB 0
#endif

#ifdef AMREX_PARTICLES
#define HAVE_PARTICLES 1
#else
#define HAVE_PARTICLES 0
#endif

#ifdef AMREX_USE_HYPRE
#define HAVE_HYPRE 1
#else
#define HAVE_HYPRE 0
#endif

#ifdef AMREX_USE_FLOAT
#define HAVE_FLOAT 1
#else
#define HAVE_FLOAT 0
#endif

static_assert(AMREX_SPACEDIM == EXPECT_SPACEDIM, "AMREX_SPACEDIM does not match the last enabled dimension");
static_assert(HAVE_MPI == EXPECT_MPI, "AMREX_USE_MPI does not match option with_mpi");
static_assert(HAVE_OPENMP == EXPECT_OPENMP, "AMREX_USE_OMP does not match option with_openmp");
static_assert(HAVE_EB == EXPECT_EB, "AMREX_USE_EB does not match option with_eb");
static_assert(HAVE_PARTICLES == EXPECT_PARTICLES, "AMREX_PARTICLES does not match option with_particles");
static_assert(HAVE_HYPRE == EXPECT_HYPRE, "AMREX_USE_HYPRE does not match option with_hypre");
static_assert(HAVE_FLOAT == EXPECT_FLOAT, "AMREX_USE_FLOAT does not match option precision");

int main(int argc, char* argv[])
{
    amrex::Initialize(argc, argv);
    {
        // A 32^dim domain split into 16^dim boxes, one ghost cell.
        amrex::Box domain(amrex::IntVect(0), amrex::IntVect(31));
        amrex::BoxArray ba(domain);
        ba.maxSize(16);
        amrex::DistributionMapping dm(ba);

        amrex::MultiFab mf(ba, dm, 1, 1);
        mf.setVal(1.0);
        amrex::Print() << "AMReX " << amrex::Version() << ", dim " << AMREX_SPACEDIM
                       << ", ranks " << amrex::ParallelDescriptor::NProcs() << "\n";
        amrex::Print() << "boxes: " << ba.size() << ", cells: " << mf.sum(0) << "\n";

#if EXPECT_LINEAR_SOLVERS
        // Solve -lap(phi) = 1 with phi = 0 on the boundary; exercises MLMG.
        amrex::RealBox real_box(AMREX_D_DECL(0.0, 0.0, 0.0), AMREX_D_DECL(1.0, 1.0, 1.0));
        amrex::Geometry geom(domain, real_box, amrex::CoordSys::cartesian,
                             {AMREX_D_DECL(0, 0, 0)});

        amrex::MultiFab phi(ba, dm, 1, 1);
        amrex::MultiFab rhs(ba, dm, 1, 0);
        phi.setVal(0.0);
        rhs.setVal(1.0);

        amrex::MLPoisson poisson({geom}, {ba}, {dm});
        poisson.setDomainBC({AMREX_D_DECL(amrex::LinOpBCType::Dirichlet,
                                          amrex::LinOpBCType::Dirichlet,
                                          amrex::LinOpBCType::Dirichlet)},
                            {AMREX_D_DECL(amrex::LinOpBCType::Dirichlet,
                                          amrex::LinOpBCType::Dirichlet,
                                          amrex::LinOpBCType::Dirichlet)});
        poisson.setLevelBC(0, &phi);

        amrex::MLMG mlmg(poisson);
        // Single precision cannot get the relative residual much below 1e-5.
        const amrex::Real tol = sizeof(amrex::Real) == sizeof(float) ? amrex::Real(1.e-4) : amrex::Real(1.e-6);
        const amrex::Real residual = mlmg.solve({&phi}, {&rhs}, tol, amrex::Real(0.0));
        amrex::Print() << "MLMG residual: " << residual << ", max phi: " << phi.max(0) << "\n";
#endif
    }
    amrex::Finalize();
    return 0;
}
