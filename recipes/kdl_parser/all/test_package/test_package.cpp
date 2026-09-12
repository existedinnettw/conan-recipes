#include <cstdio>
#include <string>

#include <kdl/tree.hpp>
#include <kdl_parser/kdl_parser.hpp>

int main()
{
    const std::string urdf =
        "<robot name=\"test_robot\">"
        "  <link name=\"base_link\"/>"
        "  <link name=\"arm_link\"/>"
        "  <joint name=\"shoulder\" type=\"revolute\">"
        "    <parent link=\"base_link\"/>"
        "    <child link=\"arm_link\"/>"
        "    <origin xyz=\"0 0 1\"/>"
        "    <axis xyz=\"0 0 1\"/>"
        "    <limit effort=\"1\" velocity=\"1\" lower=\"-1\" upper=\"1\"/>"
        "  </joint>"
        "</robot>";

    KDL::Tree tree;
    if (!kdl_parser::treeFromString(urdf, tree)) {
        std::fprintf(stderr, "Could not parse the URDF into a KDL tree\n");
        return 1;
    }

    std::printf("Tree has %u segment(s) and %u joint(s)\n",
                tree.getNrOfSegments(), tree.getNrOfJoints());

    // "base_link" becomes the tree root, "arm_link" the one segment hanging
    // off it through the single revolute joint.
    return (tree.getNrOfSegments() == 1 && tree.getNrOfJoints() == 1) ? 0 : 1;
}
