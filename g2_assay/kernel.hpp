#pragma once
#include <array>
#include <cstdint>
#include <istream>
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace mu::g2assay {
using U = std::uint64_t;
using Arc = std::array<U, 2>;
constexpr U none = std::numeric_limits<U>::max();
struct Limits { U events=6, nodes=16, edges=16, matches=256; };
struct Config {
    U nodes=0, rng=104729;
    std::string scheduler="lex_first";
    Limits limits;
    std::vector<Arc> rhs, seed;
};
struct Edge { U id, source, target, producer; };
struct Event {
    U id;
    Edge a,b;
    std::array<U,3> binding;
    std::vector<U> parents;
    U fresh, first, count, rng;
};
U read_uint(std::istream&);
U checked_add(U,U);
U uniform_index(U&,U);
Config read_config(std::istream&);
std::string config_text(const Config&);
class Graph {
    Config config_;
    bool rewired_=false;
    U intervention_prefix_=0, orientation_=0, branch_seed_=0;
    std::array<U,4> patch_{};
    std::string intervention_;
    U nodes_, next_, rng_;
    std::vector<Edge> edges_;
    std::vector<Event> events_;
public:
    explicit Graph(Config);
    std::vector<std::pair<U,U>> matches() const;
    std::string advance(int allocation_fault=0);
    void rewire(std::array<U,4>, U orientation, U branch_seed, int fault=0);
    std::string prefix(U);
    std::string run();
    std::string json(const std::string& status) const;
    std::string snapshot() const;
    std::string checkpoint() const;
    static Graph restore(const std::string&);
};
}
