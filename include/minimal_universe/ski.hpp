#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace mu {
struct Term;
using Tree = std::shared_ptr<const Term>;
struct Term {
    char atom;
    Tree left, right;
    std::uint64_t size;
    unsigned depth;
};
struct Evaluation {
    Tree term;
    std::uint64_t steps;
    std::string status;
};
Tree parse_term(const std::string& source, bool iota_only = false);
Tree translate_iota(const Tree& source, std::uint64_t cap);
Tree application(Tree left, Tree right, std::uint64_t cap);
Evaluation evaluate(Tree term, std::uint64_t max_steps, std::uint64_t max_nodes);
std::string print_term(const Tree& term);
}
