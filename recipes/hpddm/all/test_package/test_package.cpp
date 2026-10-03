// Solves a shifted 1D Laplacian (tridiagonal, SPD) with HPDDM's Krylov solvers:
// GMRES on a CSR matrix with a Jacobi preconditioner, and CG on a matrix-free
// operator, two right-hand sides each.
#include <HPDDM.hpp>

#include <cmath>
#include <cstdio>
#include <vector>

namespace {

constexpr int    n     = 200;
constexpr double shift = 0.01;

void laplacian(const double *in, double *out, int mu)
{
  for (int nu = 0; nu < mu; ++nu)
    for (int i = 0; i < n; ++i) {
      const double *x = in + nu * n;
      out[nu * n + i] = (2.0 + shift) * x[i] - (i > 0 ? x[i - 1] : 0.0) - (i < n - 1 ? x[i + 1] : 0.0);
    }
}

// CSR matrix, Jacobi preconditioner.
struct CsrOperator : HPDDM::CustomOperator<HPDDM::MatrixCSR<double>, double> {
  using HPDDM::CustomOperator<HPDDM::MatrixCSR<double>, double>::CustomOperator;
  template <bool>
  int apply(const double *const in, double *const out, const unsigned short &mu = 1, double * = nullptr, const unsigned short & = 0) const
  {
    for (int i = 0; i < mu * n_; ++i) out[i] = in[i] / (2.0 + shift);
    return 0;
  }
};

// Matrix-free, no preconditioner.
struct StencilOperator : HPDDM::EmptyOperator<double> {
  StencilOperator() : HPDDM::EmptyOperator<double>(n) { }
  int GMV(const double *const in, double *const out, const int &mu = 1) const
  {
    laplacian(in, out, mu);
    return 0;
  }
  template <bool>
  int apply(const double *const in, double *const out, const unsigned short &mu = 1, double * = nullptr, const unsigned short & = 0) const
  {
    std::copy_n(in, mu * n_, out);
    return 0;
  }
};

bool check(const char *name, int it, const std::vector<double> &b, const std::vector<double> &x, int mu)
{
  std::vector<double> r(b.size());
  laplacian(x.data(), r.data(), mu);
  bool ok = it > 0;
  for (int nu = 0; nu < mu; ++nu) {
    double nr = 0.0, nb = 0.0;
    for (int i = 0; i < n; ++i) {
      nr += (r[nu * n + i] - b[nu * n + i]) * (r[nu * n + i] - b[nu * n + i]);
      nb += b[nu * n + i] * b[nu * n + i];
    }
    const double rel = std::sqrt(nr / nb);
    std::printf("%s: %d iterations, relative residual of rhs %d = %.3e\n", name, it, nu, rel);
    ok = ok && rel < 1.0e-6;
  }
  return ok;
}

} // namespace

int main(int argc, char **argv)
{
  MPI_Init(&argc, &argv);
  std::printf("HPDDM %s\n", HPDDM_VERSION);
  const int           mu = 2;
  std::vector<double> b(mu * n);
  for (int i = 0; i < n; ++i) {
    b[i]     = 1.0;
    b[n + i] = std::sin(0.1 * i);
  }
  HPDDM::Option &opt = *HPDDM::Option::get();
  opt["tol"]         = 1.0e-10;
  opt["max_it"]      = 1000;

  // Shifted 1D Laplacian, 0-based CSR.
  auto *A = new HPDDM::MatrixCSR<double>(n, n, 3 * n - 2, false);
  int   k = 0;
  for (int i = 0; i < n; ++i) {
    A->ia_[i] = k;
    for (int j = i - 1; j <= i + 1; ++j)
      if (j >= 0 && j < n) {
        A->ja_[k]  = j;
        A->a_[k++] = j == i ? 2.0 + shift : -1.0;
      }
  }
  A->ia_[n] = k;

  bool ok = true;
  {
    opt["krylov_method"] = HPDDM_KRYLOV_METHOD_GMRES;
    opt["gmres_restart"] = 50;
    CsrOperator         op(A);
    std::vector<double> x(mu * n, 0.0);
    const int           it = HPDDM::IterativeMethod::solve(op, b.data(), x.data(), mu, MPI_COMM_SELF);
    ok                     = check("GMRES (CSR, Jacobi)", it, b, x, mu) && ok;
  }
  {
    opt["krylov_method"] = HPDDM_KRYLOV_METHOD_CG;
    StencilOperator     op;
    std::vector<double> x(mu * n, 0.0);
    const int           it = HPDDM::IterativeMethod::solve(op, b.data(), x.data(), mu, MPI_COMM_SELF);
    ok                     = check("CG (matrix-free)", it, b, x, mu) && ok;
  }
  delete A;
  MPI_Finalize();
  return ok ? 0 : 1;
}
