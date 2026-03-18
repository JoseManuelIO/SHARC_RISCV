#include <fstream>
#include <cstdint>
#include <iostream>

#include "ACC_Controller.h"
#include "debug_levels.hpp"
#include "nlohmann/json.hpp"

DebugLevels global_debug_levels;

namespace {

#if defined(__riscv)
static inline std::uint64_t read_cycle_counter() {
    std::uint64_t value = 0;
    asm volatile("rdcycle %0" : "=r"(value));
    return value;
}

static inline std::uint64_t read_instret_counter() {
    std::uint64_t value = 0;
    asm volatile("rdinstret %0" : "=r"(value));
    return value;
}
#else
static inline std::uint64_t read_cycle_counter() {
    return 0;
}

static inline std::uint64_t read_instret_counter() {
    return 0;
}
#endif

}  // namespace

class ACCReplayController : public ACC_Controller {
public:
    using ACC_Controller::ACC_Controller;

    void seedControl(const uVec &u) {
        control = u;
    }
};

int main(int argc, char **argv) {
    if (argc != 3) {
        std::cerr << "usage: cva6_acc_runtime <config.json> <snapshot.json>\n";
        return 2;
    }

    nlohmann::json config;
    nlohmann::json snapshot;

    {
        std::ifstream f(argv[1]);
        if (!f.is_open()) {
            std::cerr << "CONFIG_OPEN_FAIL\n";
            return 3;
        }
        f >> config;
    }

    {
        std::ifstream f(argv[2]);
        if (!f.is_open()) {
            std::cerr << "SNAPSHOT_OPEN_FAIL\n";
            return 4;
        }
        f >> snapshot;
    }

    global_debug_levels.from_json(config.at("==== Debgugging Levels ===="));

    ACCReplayController controller(config);

    xVec x;
    x << snapshot.at("x").at(0).get<double>(),
         snapshot.at("x").at(1).get<double>(),
         snapshot.at("x").at(2).get<double>();

    wVec w;
    w << snapshot.at("w").at(0).get<double>(),
         snapshot.at("w").at(1).get<double>();

    uVec u_prev;
    u_prev << snapshot.at("u_prev").at(0).get<double>(),
              snapshot.at("u_prev").at(1).get<double>();

    controller.seedControl(u_prev);
    std::uint64_t cycle_start = read_cycle_counter();
    std::uint64_t instret_start = read_instret_counter();
    controller.calculateControl(
        snapshot.at("k").get<int>(),
        snapshot.at("t").get<double>(),
        x,
        w);
    std::uint64_t cycle_end = read_cycle_counter();
    std::uint64_t instret_end = read_instret_counter();

    uVec u = controller.getLatestControl();
    nlohmann::json metadata = controller.getLatestMetadata();
    std::uint64_t delta_cycles = cycle_end >= cycle_start ? (cycle_end - cycle_start) : 0;
    std::uint64_t delta_instret = instret_end >= instret_start ? (instret_end - instret_start) : 0;
    metadata["cycles"] = delta_cycles;
    metadata["instret"] = delta_instret;
    metadata["cpi"] = delta_instret > 0 ? static_cast<double>(delta_cycles) / static_cast<double>(delta_instret) : 0.0;
    metadata["ipc"] = delta_cycles > 0 ? static_cast<double>(delta_instret) / static_cast<double>(delta_cycles) : 0.0;

    nlohmann::json out;
    out["snapshot_id"] = snapshot.at("snapshot_id");
    out["k"] = snapshot.at("k");
    out["t"] = snapshot.at("t");
    out["x"] = snapshot.at("x");
    out["w"] = snapshot.at("w");
    out["u_prev"] = snapshot.at("u_prev");
    out["u"] = {u(0), u(1)};
    out["metadata"] = metadata;

    std::cout << out.dump(2) << std::endl;
    return 0;
}
