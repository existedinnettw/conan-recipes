#include <PxPhysicsAPI.h>

#include <iostream>

using namespace physx;

int main() {
    static PxDefaultAllocator allocator;
    static PxDefaultErrorCallback errorCallback;

    PxFoundation* foundation = PxCreateFoundation(PX_PHYSICS_VERSION, allocator, errorCallback);
    PxPhysics* physics = PxCreatePhysics(PX_PHYSICS_VERSION, *foundation, PxTolerancesScale());
    PxDefaultCpuDispatcher* dispatcher = PxDefaultCpuDispatcherCreate(1);

    PxSceneDesc sceneDesc(physics->getTolerancesScale());
    sceneDesc.gravity = PxVec3(0.0f, -9.81f, 0.0f);
    sceneDesc.cpuDispatcher = dispatcher;
    sceneDesc.filterShader = PxDefaultSimulationFilterShader;
    PxScene* scene = physics->createScene(sceneDesc);

    PxMaterial* material = physics->createMaterial(0.5f, 0.5f, 0.6f);
    PxRigidDynamic* box = PxCreateDynamic(*physics, PxTransform(PxVec3(0, 10, 0)), PxBoxGeometry(1, 1, 1), *material, 1.0f);
    scene->addActor(*box);

    // PhysXCooking: build a convex mesh from the corners of a unit cube.
    const PxVec3 corners[] = {{-1, -1, -1}, {1, -1, -1}, {-1, 1, -1}, {1, 1, -1},
                              {-1, -1, 1},  {1, -1, 1},  {-1, 1, 1},  {1, 1, 1}};
    PxConvexMeshDesc convexDesc;
    convexDesc.points.count = 8;
    convexDesc.points.stride = sizeof(PxVec3);
    convexDesc.points.data = corners;
    convexDesc.flags = PxConvexFlag::eCOMPUTE_CONVEX;
    PxConvexMesh* convex = PxCreateConvexMesh(PxCookingParams(physics->getTolerancesScale()), convexDesc,
                                              physics->getPhysicsInsertionCallback());

    for (int i = 0; i < 60; ++i) {
        scene->simulate(1.0f / 60.0f);
        scene->fetchResults(true);
    }
    std::cout << "PhysX " << PX_PHYSICS_VERSION_MAJOR << "." << PX_PHYSICS_VERSION_MINOR << "."
              << PX_PHYSICS_VERSION_BUGFIX << ": box y after 1 s = " << box->getGlobalPose().p.y
              << ", convex hull vertices = " << convex->getNbVertices() << std::endl;

    convex->release();
    scene->release();
    dispatcher->release();
    physics->release();
    foundation->release();
    return 0;
}
