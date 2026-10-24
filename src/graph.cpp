#include "minimal_universe/graph.hpp"
#include <algorithm>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace mu {
namespace {
void demand(bool valid, const char* why) {
    if (!valid) throw std::invalid_argument(why);
}
U64 read_uint(std::istream& in) {
    std::string token;
    demand(bool(in >> token), "missing integer");
    demand(!token.empty() && token.find_first_not_of("0123456789") == std::string::npos,
           "invalid unsigned integer");
    std::size_t used = 0;
    const auto result = std::stoull(token, &used);
    demand(used == token.size(), "invalid integer suffix");
    return result;
}
void end(std::istream& in) {
    in >> std::ws;
    demand(in.eof(), "trailing data");
}
Config read_config(std::istream& in) {
    std::string version;
    demand(bool(in >> version) && version == "MU_CONFIG_1", "unsupported config version");
    Config c;
    c.nodes = read_uint(in); c.rng = read_uint(in);
    demand(bool(in >> c.scheduler), "missing scheduler");
    c.limits = {read_uint(in), read_uint(in), read_uint(in)};
    auto k = read_uint(in);
    demand(k <= 3, "RHS exceeds grammar");
    for (U64 i = 0; i < k; ++i) {
        auto a = read_uint(in), b = read_uint(in);
        demand(a < 3 && b < 3, "invalid rule endpoint");
        c.rule.push_back({unsigned(a), unsigned(b)});
    }
    auto n = read_uint(in);
    demand(n <= 4096, "seed too large for reference kernel");
    for (U64 i = 0; i < n; ++i) c.seed.push_back({read_uint(in), read_uint(in)});
    return c;
}
void nullable(std::ostream& out, U64 value) {
    if (value == no_parent) out << "null"; else out << value;
}
}
U64 checked_add(U64 a, U64 b) {
    if (b > no_parent - a) throw std::overflow_error("counter overflow");
    return a + b;
}
U64 random_word(U64& state) {
    // SplitMix64: unsigned arithmetic deliberately wraps modulo 2^64.
    state += 0x9e3779b97f4a7c15ULL;
    U64 z = state;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
U64 uniform_index(U64& state, U64 bound) {
    demand(bound > 0, "empty uniform sample");
    const U64 threshold = (U64(0) - bound) % bound;
    for (;;) { auto word = random_word(state); if (word >= threshold) return word % bound; }
}
Config parse_config(const std::string& text) {
    demand(text.size() <= 1024 * 1024, "config too large");
    std::istringstream in(text);
    auto config = read_config(in); end(in); return config;
}
std::string config_text(const Config& c) {
    std::ostringstream out;
    out << "MU_CONFIG_1\n" << c.nodes << ' ' << c.rng << ' ' << c.scheduler << '\n'
        << c.limits.events << ' ' << c.limits.nodes << ' ' << c.limits.edges << '\n'
        << c.rule.size() << '\n';
    for (auto arc : c.rule) out << arc[0] << ' ' << arc[1] << '\n';
    out << c.seed.size() << '\n';
    for (auto arc : c.seed) out << arc[0] << ' ' << arc[1] << '\n';
    return out.str();
}
Graph::Graph(Config config) : config_(std::move(config)), nodes_(config_.nodes),
    next_edge_(config_.seed.size()), rng_(config_.rng) {
    demand(config_.scheduler == "oldest" || config_.scheduler == "newest" ||
           config_.scheduler == "uniform", "invalid scheduler");
    demand(config_.rule.size() <= 3, "RHS exceeds grammar");
    demand(std::is_sorted(config_.rule.begin(), config_.rule.end()), "rule must be sorted");
    for (auto arc : config_.rule) demand(arc[0] < 3 && arc[1] < 3, "invalid rule endpoint");
    demand(config_.limits.events <= 100000 && config_.limits.nodes <= 100000 &&
           config_.limits.edges <= 100000, "reference safety ceiling exceeded");
    demand(nodes_ <= config_.limits.nodes && config_.seed.size() <= config_.limits.edges,
           "initial state exceeds cap");
    for (auto arc : config_.seed) {
        demand(arc[0] < nodes_ && arc[1] < nodes_, "invalid seed endpoint");
        edges_.push_back({edges_.size(), arc[0], arc[1], no_parent});
    }
}
std::string Graph::advance() {
    if (edges_.empty()) return "no_eligible_edge";
    if (history_.size() >= config_.limits.events) return "event_cap";
    bool fresh = false;
    for (auto arc : config_.rule) fresh = fresh || arc[0] == 2 || arc[1] == 2;
    const auto new_nodes = checked_add(nodes_, fresh);
    const auto new_edges = checked_add(edges_.size() - 1, config_.rule.size());
    const auto new_next = checked_add(next_edge_, config_.rule.size());
    if (new_nodes > config_.limits.nodes) return "node_cap";
    if (new_edges > config_.limits.edges) return "edge_cap";
    auto next_rng = rng_;
    auto index = config_.scheduler == "newest" ? edges_.size() - 1 : 0;
    if (config_.scheduler == "uniform") index = uniform_index(next_rng, edges_.size());
    const auto selected = edges_.at(index);
    // Prepare all allocations before commit, including the event history.
    auto next_edges = edges_;
    next_edges.erase(next_edges.begin() + static_cast<std::ptrdiff_t>(index));
    const std::array<U64, 3> binding{selected.source, selected.target, nodes_};
    for (std::size_t i = 0; i < config_.rule.size(); ++i) {
        auto arc = config_.rule[i];
        next_edges.push_back({next_edge_ + i, binding[arc[0]], binding[arc[1]], history_.size()});
    }
    auto next_history = history_;
    next_history.push_back({history_.size(), selected.id, selected.source, selected.target,
                           selected.parent, fresh ? nodes_ : no_parent, next_edge_,
                           config_.rule.size(), next_rng});
    edges_.swap(next_edges); history_.swap(next_history);
    nodes_ = new_nodes; next_edge_ = new_next; rng_ = next_rng;
    return "applied";
}
std::string Graph::run(U64 stop_after) {
    while (history_.size() < stop_after) {
        auto status = advance(); if (status != "applied") return status;
    }
    return "paused";
}
std::string Graph::checkpoint() const {
    std::ostringstream out;
    out << "MU_CHECKPOINT_1\n" << config_text(config_) << history_.size() << '\n';
    for (auto e : history_) out << e.consumed << '\n';
    out << "STATE\n" << nodes_ << ' ' << next_edge_ << ' ' << rng_ << ' ' << edges_.size() << '\n';
    for (auto e : edges_) out << e.id << ' ' << e.source << ' ' << e.target << ' ' << e.parent << '\n';
    return out.str();
}
Graph Graph::restore(const std::string& text) {
    demand(text.size() <= 32 * 1024 * 1024, "checkpoint too large");
    std::istringstream in(text);
    std::string version;
    demand(bool(in >> version) && version == "MU_CHECKPOINT_1", "unsupported checkpoint version");
    Graph graph(read_config(in));
    const auto count = read_uint(in);
    demand(count <= graph.config_.limits.events, "checkpoint event limit");
    for (U64 i = 0; i < count; ++i) {
        auto expected = read_uint(in);
        demand(graph.advance() == "applied", "invalid checkpoint history");
        demand(graph.history_.back().consumed == expected, "checkpoint choice mismatch");
    }
    // Full canonical-byte comparison validates state, RNG, counters, trailing data,
    // and serialization version. This is semantic integrity, not authentication.
    demand(graph.checkpoint() == text, "checkpoint state/serialization mismatch");
    return graph;
}
std::string Graph::json(const std::string& status) const {
    std::ostringstream out;
    out << "{\"status\":\"" << status << "\",\"nodes\":" << nodes_
        << ",\"next_edge\":" << next_edge_ << ",\"rng\":" << rng_ << ",\"edges\":[";
    bool first = true;
    for (auto e : edges_) {
        if (!first) out << ',';
        first = false;
        out << '[' << e.id << ',' << e.source << ',' << e.target << ',';
        nullable(out, e.parent); out << ']';
    }
    out << "],\"events\":["; first = true;
    for (auto e : history_) {
        if (!first) out << ',';
        first = false;
        out << '[' << e.index << ',' << e.consumed << ',' << e.source << ',' << e.target << ',';
        nullable(out, e.parent); out << ','; nullable(out, e.created_node);
        out << ',' << e.first_edge << ',' << e.count << ',' << e.rng << ']';
    }
    out << "]}"; return out.str();
}
}
