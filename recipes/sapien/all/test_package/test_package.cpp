#include <sapien/entity.h>
#include <sapien/physx/collision_shape.h>
#include <sapien/physx/material.h>
#include <sapien/physx/physx_system.h>
#include <sapien/physx/rigid_component.h>
#include <sapien/scene.h>

#include <iostream>
#include <memory>

using sapien::Entity;
using sapien::Pose;
using sapien::Scene;
using sapien::Vec3;

int main() {
    auto scene = std::make_shared<Scene>();
    scene->addSystem(std::make_shared<sapien::physx::PhysxSystemCpu>());
    auto material = std::make_shared<sapien::physx::PhysxMaterial>(0.3f, 0.3f, 0.1f);

    auto ground = std::make_shared<Entity>();
    auto groundBody = std::make_shared<sapien::physx::PhysxRigidStaticComponent>();
    auto plane = std::make_shared<sapien::physx::PhysxCollisionShapePlane>(material);
    // PhysX planes face +x; rotate the normal to +z.
    plane->setLocalPose(Pose({0.f, 0.f, 0.f}, {0.7071068f, 0.f, -0.7071068f, 0.f}));
    groundBody->attachCollision(plane);
    ground->addComponent(groundBody);
    scene->addEntity(ground);

    auto box = std::make_shared<Entity>();
    auto boxBody = std::make_shared<sapien::physx::PhysxRigidDynamicComponent>();
    boxBody->attachCollision(std::make_shared<sapien::physx::PhysxCollisionShapeBox>(Vec3(0.1f, 0.1f, 0.1f), material));
    box->addComponent(boxBody);
    box->setPose(Pose(Vec3(0.f, 0.f, 1.f)));
    scene->addEntity(box);

    for (int i = 0; i < 200; ++i) {
        scene->step();
    }
    std::cout << "SAPIEN box z after 200 steps: " << box->getPose().p.z << std::endl;
    return 0;
}
