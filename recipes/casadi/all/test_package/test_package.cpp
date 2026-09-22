#include <cstdio>

#include <casadi/casadi.hpp>

#if CASADI_STATIC
extern "C" void casadi_load_nlpsol_sqpmethod();
extern "C" void casadi_load_conic_qrqp();
#endif

int main() {
  // Symbolics plus algorithmic differentiation: the core of what casadi is for.
  casadi::SX x = casadi::SX::sym("x");
  casadi::SX y = casadi::SX::sym("y");
  casadi::SX f = x * x + 3 * x * y;

  casadi::Function fun("fun", {x, y}, {f, casadi::SX::jacobian(f, x)});
  std::vector<casadi::DM> res = fun(std::vector<casadi::DM>{2.0, 5.0});

  std::printf("casadi %s\n", casadi::CasadiMeta::version());
  std::printf("f(2,5) = %g, df/dx(2,5) = %g\n",
              static_cast<double>(res.at(0)), static_cast<double>(res.at(1)));

  // A solver comes from a plugin, so this also checks that the plugins are reachable.
  // Minimize (x-1)^2 + (y-2)^2, whose solution is (1, 2).
#if CASADI_STATIC
  // A static casadi has nothing to dlopen, so the plugins linked into the executable
  // have to register themselves; sqpmethod solves its QP subproblems with qrqp.
  casadi_load_nlpsol_sqpmethod();
  casadi_load_conic_qrqp();
#endif
  casadi::SX v = casadi::SX::vertcat({x, y});
  casadi::SXDict nlp = {{"x", v}, {"f", pow(x - 1, 2) + pow(y - 2, 2)}};
  // qrqp instead of the default qpoases, which is only built with -o with_qpoases=True.
  casadi::Dict opts = {{"qpsol", std::string("qrqp")}, {"print_iteration", false},
                       {"print_time", false}};
  casadi::Function solver = casadi::nlpsol("solver", "sqpmethod", nlp, opts);
  casadi::DMDict sol = solver(casadi::DMDict{{"x0", casadi::DM::zeros(2)}});
  std::vector<double> xopt = std::vector<double>(sol.at("x"));
  std::printf("argmin = (%g, %g)\n", xopt.at(0), xopt.at(1));

  return 0;
}
