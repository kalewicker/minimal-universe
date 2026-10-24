#pragma once
#include <array>
#include <cstdint>
#include <limits>
#include <string>
#include <vector>

namespace mu {
using U64 = std::uint64_t;
constexpr U64 no_parent = std::numeric_limits<U64>::max();
struct Edge {
    U64 id, source, target, parent = no_parent;
    bool operator==(const Edge&) const = default;
};
struct Limits { U64 events = 12, nodes = 64, edges = 64; };
struct Config {
    U64 nodes = 0, rng = 0;
    std::vector<std::array<unsigned, 2>> rule;
    std::vector<std::array<U64, 2>> seed;
    std::string scheduler = "oldest";
    Limits limits;
};
struct Event {
    U64 index, consumed, source, target, parent, created_node, first_edge, count, rng;
    bool operator==(const Event&) const = default;
};
U64 random_word(U64& state);
U64 uniform_index(U64& state, U64 bound);
U64 checked_add(U64 a, U64 b);
Config parse_config(const std::string& text);
std::string config_text(const Config& config);
class Graph {
public:
    explicit Graph(Config config);
    // Rejection leaves graph, history, counters, and RNG byte-for-byte unchanged.
    std::string advance();
    std::string run(U64 stop_after = no_parent);
    std::string checkpoint() const;
    static Graph restore(const std::string& text);
    std::string json(const std::string& status) const;
    const std::vector<Edge>& edges() const { return edges_; }
    const std::vector<Event>& events() const { return history_; }
    U64 nodes() const { return nodes_; }
    U64 rng() const { return rng_; }
private:
    Config config_;
    U64 nodes_, next_edge_, rng_;
    std::vector<Edge> edges_;
    std::vector<Event> history_;
};
}
