#include <cstdio>

#include <kdl/chain.hpp>
#include <kdl/chainfksolverpos_recursive.hpp>
#include <kdl/config.h>
#include <kdl/frames.hpp>
#include <kdl/utilities/utility.h>

int main()
{
    KDL::Chain chain;
    chain.addSegment(KDL::Segment(KDL::Joint(KDL::Joint::RotZ),
                                  KDL::Frame(KDL::Vector(1.0, 0.0, 0.0))));

    KDL::ChainFkSolverPos_recursive solver(chain);
    KDL::JntArray q(chain.getNrOfJoints());
    q(0) = KDL::PI / 2.0;

    KDL::Frame pose;
    if (solver.JntToCart(q, pose) < 0) {
        return 1;
    }

    std::printf("KDL %s: tip at (%.3f, %.3f, %.3f)\n",
                KDL_VERSION_STRING, pose.p.x(), pose.p.y(), pose.p.z());

    // Rotating the unit-X segment by 90 degrees puts the tip on +Y.
    return KDL::Equal(pose.p, KDL::Vector(0.0, 1.0, 0.0)) ? 0 : 1;
}
