#include <hybrid_astar/algorithm.h>
#include <hybrid_astar/smoother.h>

#include <cstdio>
#include <memory>
#include <vector>

using namespace HybridAStar;

int main() {
  const int width = 60;
  const int height = 60;

  auto grid = std::make_shared<OccupancyGrid>();
  grid->info.width = width;
  grid->info.height = height;
  grid->data.assign(width * height, 0);
  // a wall up the middle of the lower half of the map
  for (int y = 0; y < 30; ++y) {
    grid->data[y * width + 30] = 100;
  }

  // The collision lookup table is large, keep it off the stack.
  auto configurationSpace = std::make_unique<CollisionDetection>();
  configurationSpace->updateGrid(grid);

  // DynamicVoronoi takes ownership of this map and frees it.
  bool** binMap = new bool*[width];
  for (int x = 0; x < width; ++x) {
    binMap[x] = new bool[height];
    for (int y = 0; y < height; ++y) {
      binMap[x][y] = grid->data[y * width + x] != 0;
    }
  }
  DynamicVoronoi voronoi;
  voronoi.initializeMap(width, height, binMap);
  voronoi.update();

  std::vector<Node3D> nodes3D(width * height * Constants::headings);
  std::vector<Node2D> nodes2D(width * height);
  std::vector<float> dubinsLookup(1);

  // heading north on one side of the wall, to heading south on the other
  Node3D start(15, 10, M_PI / 2, 0, 0, nullptr);
  const Node3D goal(45, 10, 3 * M_PI / 2, 0, 0, nullptr);
  Node3D* solution = Algorithm::hybridAStar(start, goal, nodes3D.data(), nodes2D.data(), width, height,
                                            *configurationSpace, dubinsLookup.data());
  // The search returns its last node when it runs out of iterations.
  if (solution == nullptr || !(*solution == goal)) {
    std::printf("no path found\n");
    return 1;
  }

  Smoother smoother;
  smoother.tracePath(solution);
  const std::size_t raw = smoother.getPath().size();
  smoother.smoothPath(voronoi);
  std::printf("path with %zu poses, smoothed to end at (%.1f, %.1f)\n", raw, smoother.getPath().front().getX(),
              smoother.getPath().front().getY());
  return raw > 1 ? 0 : 1;
}
