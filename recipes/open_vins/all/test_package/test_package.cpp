#include "core/VioManagerOptions.h"
#include "state/State.h"
#include "utils/Loader.h"
#include "utils/print.h"

#include <iostream>

int main()
{
  ov_core::Printer::setPrintLevel(ov_core::Printer::PrintLevel::WARNING);
  ov_msckf::VioManagerOptions options;
  ov_msckf::State state(options.state_options);
  const double length = ov_eval::Loader::get_total_length({});
  std::cout << "open_vins: state size " << state.max_covariance_size() << ", length " << length << std::endl;
  return 0;
}
