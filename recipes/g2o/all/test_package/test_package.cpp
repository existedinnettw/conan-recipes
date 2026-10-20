#include <g2o/core/block_solver.h>
#include <g2o/core/optimization_algorithm_levenberg.h>
#include <g2o/core/sparse_optimizer.h>
#include <g2o/solvers/eigen/linear_solver_eigen.h>
#include <g2o/types/sba/types_six_dof_expmap.h>
#ifdef TEST_CSPARSE
#include <g2o/solvers/csparse/linear_solver_csparse.h>
#endif

#include <iostream>
#include <memory>

// Estimate a 3D point from its observation by one fixed camera pose.
template <typename LinearSolver>
double solve()
{
    using BlockSolver = g2o::BlockSolver_6_3;
    auto algorithm = new g2o::OptimizationAlgorithmLevenberg(
        std::make_unique<BlockSolver>(std::make_unique<LinearSolver>()));
    g2o::SparseOptimizer optimizer;
    optimizer.setAlgorithm(algorithm);

    auto* pose = new g2o::VertexSE3Expmap();
    pose->setId(0);
    pose->setEstimate(g2o::SE3Quat());
    pose->setFixed(true);
    optimizer.addVertex(pose);

    auto* point = new g2o::VertexPointXYZ();
    point->setId(1);
    point->setEstimate(Eigen::Vector3d(0.2, -0.1, 1.0));
    optimizer.addVertex(point);

    auto* edge = new g2o::EdgeSE3ProjectXYZ();
    edge->setVertex(0, point);
    edge->setVertex(1, pose);
    edge->setMeasurement(Eigen::Vector2d(320.0, 240.0));
    edge->setInformation(Eigen::Matrix2d::Identity());
    edge->fx = edge->fy = 500.0;
    edge->cx = 320.0;
    edge->cy = 240.0;
    optimizer.addEdge(edge);

    optimizer.initializeOptimization();
    optimizer.optimize(10);
    edge->computeError();
    return edge->chi2();
}

int main()
{
    double chi2 = solve<g2o::LinearSolverEigen<g2o::BlockSolver_6_3::PoseMatrixType>>();
    std::cout << "eigen chi2: " << chi2 << std::endl;
#ifdef TEST_CSPARSE
    double chi2_cs = solve<g2o::LinearSolverCSparse<g2o::BlockSolver_6_3::PoseMatrixType>>();
    std::cout << "csparse chi2: " << chi2_cs << std::endl;
    chi2 += chi2_cs;
#endif
    return chi2 < 1.0 ? 0 : 1; // initial chi2 is 12500
}
