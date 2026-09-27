/* Co-simulates an FMU exported by OpenModelica (x' = -x, x(0) = 1) for 1 s. */
#include <OMSimulator/OMSimulator.h>

#include <math.h>
#include <stdio.h>

#define CHECK(call)                              \
  if ((call) != oms_status_ok) {                 \
    fprintf(stderr, "%s failed\n", #call);       \
    return 1;                                    \
  }

int main(void)
{
  double x = 0.0;

  printf("OMSimulator %s\n", oms_getVersion());

  CHECK(oms_setTempDirectory("oms-temp"))
  CHECK(oms_newModel("model"))
  CHECK(oms_addSystem("model.root", oms_system_wc))
  CHECK(oms_addSubModel("model.root.decay", DECAY_FMU))
  CHECK(oms_setResultFile("model", "", 0))
  CHECK(oms_setFixedStepSize("model.root", 0.01))
  CHECK(oms_setStopTime("model", 1.0))
  CHECK(oms_instantiate("model"))
  CHECK(oms_initialize("model"))
  CHECK(oms_simulate("model"))
  CHECK(oms_getReal("model.root.decay.x", &x))
  CHECK(oms_terminate("model"))
  CHECK(oms_delete("model"))

  printf("x(1) = %f, exp(-1) = %f\n", x, exp(-1.0));
  /* The FMU steps with explicit Euler by default: (1 - dt)^100 = 0.366. */
  return fabs(x - exp(-1.0)) < 1e-2 ? 0 : 1;
}
