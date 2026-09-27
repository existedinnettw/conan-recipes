#include <ctpl_stl.h>

#include <future>
#include <iostream>
#include <vector>

int main()
{
  ctpl::thread_pool pool(4);
  std::vector<std::future<int>> results;
  for (int i = 1; i <= 10; ++i)
    results.push_back(pool.push([i](int /* thread id */) { return i * i; }));

  int sum = 0;
  for (auto& result : results)
    sum += result.get();
  std::cout << "sum of squares 1..10 = " << sum << std::endl;
  return sum == 385 ? 0 : 1;
}
