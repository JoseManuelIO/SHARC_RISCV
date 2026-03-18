#include <fstream>
#include <iostream>

#include "ACC_Controller.h"
#include "debug_levels.hpp"
#include "nlohmann/json.hpp"

DebugLevels global_debug_levels;

class ACCReplayController : public ACC_Controller {
public:
    using ACC_Controller::ACC_Controller;

    void seedControl(const uVec &u) {
        control = u;
    }
};

int main(int argc, char **argv) {
    if (argc != 3) {
        std::cerr << "usage: acc_snapshot_host <config.json> <snapshot.json>\n";
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
    controller.calculateControl(
        snapshot.at("k").get<int>(),
        snapshot.at("t").get<double>(),
        x,
        w);

    uVec u = controller.getLatestControl();
    nlohmann::json metadata = controller.getLatestMetadata();

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
