#include <iostream>

#include <mpc/LMPC.hpp>

int main() {
    constexpr int Tnx = 2;
    constexpr int Tny = 2;
    constexpr int Tnu = 1;
    constexpr int Tndu = 0;
    constexpr int Tph = 5;
    constexpr int Tch = 5;

    mpc::LMPC<Tnx, Tnu, Tndu, Tny, Tph, Tch> controller;
    controller.setLoggerLevel(mpc::Logger::log_level::NONE);

    mpc::mat<Tnx, Tnx> A, Ad;
    A << 0.0, 1.0,
         0.0, 2.0;

    mpc::mat<Tnx, Tnu> B, Bd;
    B << 0.0,
         1.0;

    mpc::discretization<Tnx, Tnu>(A, B, 0.001, Ad, Bd);

    mpc::mat<Tny, Tnx> C;
    C.setIdentity();

    controller.setStateSpaceModel(Ad, Bd, C);

    mpc::cvec<Tnu> input_w;
    mpc::cvec<Tnu> delta_input_w;
    mpc::cvec<Tny> output_w;

    output_w << 1.0, 0.0;
    input_w << 0.1;
    delta_input_w << 0.0;

    controller.setObjectiveWeights(output_w, input_w, delta_input_w, {-1, -1});
    controller.setReferences(
        mpc::mat<Tny, Tph>::Zero(),
        mpc::mat<Tnu, Tph>::Zero(),
        mpc::mat<Tnu, Tph>::Zero());

    mpc::cvec<Tnx> x0;
    x0 << 10.0, 0.0;
    mpc::cvec<Tnu> u0;
    u0 << 0.0;

    mpc::LParameters params;
    params.maximum_iteration = 4000;
    params.verbose = false;
    controller.setOptimizerParameters(params);

    auto res = controller.optimize(x0, u0);
    auto seq = controller.getOptimalSequence();

    std::cout << "LIBMPC_PROBE_OK" << std::endl;
    std::cout << "solver_status=" << res.solver_status << std::endl;
    std::cout << "status_enum=" << static_cast<int>(res.status) << std::endl;
    std::cout << "iterations=" << res.num_iterations << std::endl;
    std::cout << "cost=" << res.cost << std::endl;
    std::cout << "cmd0=" << res.cmd(0) << std::endl;
    std::cout << "seq_input0=" << seq.input(0, 0) << std::endl;
    std::cout << "seq_state0_0=" << seq.state(0, 0) << std::endl;
    std::cout << "seq_state0_1=" << seq.state(0, 1) << std::endl;

    return 0;
}
