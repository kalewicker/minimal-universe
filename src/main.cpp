#include "minimal_universe/graph.hpp"
#include "minimal_universe/ski.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace {
std::string read(const std::string& path) {
    if (std::filesystem::file_size(path) > 32 * 1024 * 1024) throw std::runtime_error("file byte limit");
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot read file");
    std::ostringstream out; out << in.rdbuf(); return out.str();
}
mu::U64 number(const std::string& s) {
    if (s.empty() || s.find_first_not_of("0123456789") != std::string::npos)
        throw std::invalid_argument("expected unsigned decimal");
    return std::stoull(s);
}
}
int main(int argc, char** argv) {
    try {
        if (argc < 3) throw std::invalid_argument(
            "usage: msru graph CONFIG [PAUSE_AFTER CHECKPOINT] | resume CHECKPOINT | "
            "iota SOURCE STEPS NODES [PROBE...] | ski TERM STEPS NODES");
        std::string mode = argv[1];
        if (mode == "graph" || mode == "resume") {
            if ((mode == "graph" && argc != 3 && argc != 5) || (mode == "resume" && argc != 3))
                throw std::invalid_argument("invalid graph arguments");
            auto graph = mode == "graph" ? mu::Graph(mu::parse_config(read(argv[2])))
                                          : mu::Graph::restore(read(argv[2]));
            auto status = graph.run(argc == 5 ? number(argv[3]) : mu::no_parent);
            if (argc == 5) {
                if (std::filesystem::exists(argv[4])) throw std::runtime_error("checkpoint already exists");
                std::ofstream out(argv[4]); out << graph.checkpoint(); out.close();
                if (!out) throw std::runtime_error("checkpoint write failed");
            }
            std::cout << graph.json(status) << '\n';
        } else if (mode == "iota" || mode == "ski") {
            if (argc < 5 || (mode == "ski" && argc != 5)) throw std::invalid_argument("invalid term arguments");
            auto steps = number(argv[3]), cap = number(argv[4]);
            if (cap == 0 || cap > 100000 || steps > 100000) throw std::invalid_argument("budget out of range");
            auto term = mu::parse_term(argv[2], mode == "iota");
            if (mode == "iota") term = mu::translate_iota(term, cap);
            for (int j = 5; j < argc; ++j) term = mu::application(term, mu::parse_term(argv[j]), cap);
            auto result = mu::evaluate(term, steps, cap);
            std::cout << "{\"status\":\"" << result.status << "\",\"steps\":" << result.steps
                      << ",\"nodes\":" << result.term->size << ",\"term\":\""
                      << mu::print_term(result.term) << "\"}\n";
        } else throw std::invalid_argument("unknown mode");
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n'; return 2;
    }
}
