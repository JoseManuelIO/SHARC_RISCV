#include <Eigen/Dense>
#include <cmath>
#include <iostream>

int main() {
    Eigen::Matrix3d A;
    A << 4.0, 1.0, 2.0,
         1.0, 3.0, 0.5,
         2.0, 0.5, 5.0;

    Eigen::Vector3d b;
    b << 1.0, 2.0, 3.0;

    Eigen::Vector3d x = A.ldlt().solve(b);
    Eigen::Matrix3d C = A * A.transpose();
    double checksum = C.sum() + x.sum();

    if (!std::isfinite(checksum)) {
        std::cerr << "EIGEN_PROBE_FAIL_NONFINITE" << std::endl;
        return 2;
    }

    std::cout << "EIGEN_PROBE_OK" << std::endl;
    std::cout << "x0=" << x(0) << std::endl;
    std::cout << "x1=" << x(1) << std::endl;
    std::cout << "x2=" << x(2) << std::endl;
    std::cout << "checksum=" << checksum << std::endl;
    return 0;
}
