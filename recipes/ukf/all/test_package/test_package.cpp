#include <cmath>

#include <Eigen/Core>

#include <UKF/Types.h>
#include <UKF/Integrator.h>
#include <UKF/StateVector.h>
#include <UKF/MeasurementVector.h>
#include <UKF/Core.h>

enum StateFields { Position, Velocity };
enum MeasurementFields { GPS_Position };

using MyStateVector = UKF::StateVector<
    UKF::Field<Position, UKF::Vector<3>>,
    UKF::Field<Velocity, UKF::Vector<3>>
>;

using MyMeasurementVector = UKF::FixedMeasurementVector<
    UKF::Field<GPS_Position, UKF::Vector<3>>
>;

using Filter = UKF::Core<MyStateVector, MyMeasurementVector, UKF::IntegratorRK4>;

namespace UKF {

template <> template <>
MyStateVector MyStateVector::derivative<>() const {
    MyStateVector temp;
    temp.set_field<Position>(get_field<Velocity>());
    temp.set_field<Velocity>(UKF::Vector<3>(0, 0, 0));
    return temp;
}

template <> template <>
UKF::Vector<3> MyMeasurementVector::expected_measurement<MyStateVector, GPS_Position>(
        const MyStateVector& state) {
    return state.get_field<Position>();
}

}

int main()
{
    // Scenario: A constant-velocity filter converges on a fixed GPS fix.
    // Given a filter at the origin with a large position uncertainty.
    Filter filter;
    filter.state.set_field<Position>(UKF::Vector<3>(0, 0, 0));
    filter.state.set_field<Velocity>(UKF::Vector<3>(0, 0, 0));
    filter.covariance = MyStateVector::CovarianceMatrix::Identity() * 100;
    filter.process_noise_covariance = MyStateVector::CovarianceMatrix::Identity() * 1e-4;
    filter.measurement_covariance << 1, 1, 1;

    MyMeasurementVector measurement;
    measurement.set_field<GPS_Position>(UKF::Vector<3>(10, -5, 2));

    // When the filter fuses the same measurement repeatedly.
    for (int i = 0; i < 100; ++i) {
        filter.step(0.01, measurement);
    }

    // Then the position estimate is close to the measurement.
    const UKF::Vector<3> error =
        filter.state.get_field<Position>() - UKF::Vector<3>(10, -5, 2);
    return error.norm() < 0.5 ? 0 : 1;
}
