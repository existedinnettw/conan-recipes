#include "common/VectorMath.hpp"
#include "vehicles/vessel/api/VesselRpcLibClient.hpp"

#include <iostream>

int main()
{
    using namespace msr::airlib;

    // No simulator runs here: the client only starts connecting, so the state must not be Connected.
    VesselRpcLibClient client("127.0.0.1", 1, 1);
    const auto state = client.getConnectionState();
    std::cout << "connection state: " << static_cast<int>(state) << std::endl;

    const Quaternionr q = VectorMath::toQuaternion(0, 0, 1.5707963f);
    const Vector3r v = VectorMath::rotateVector(Vector3r(1, 0, 0), q, true);
    std::cout << "rotated: " << v.x() << " " << v.y() << " " << v.z() << std::endl;

    return state == RpcLibClientBase::ConnectionState::Connected ? 1 : 0;
}
