#include "minimal_universe/ski.hpp"
#include <algorithm>
#include <cctype>
#include <stdexcept>
#include <utility>

namespace mu {
namespace {
struct TermCap : std::runtime_error { TermCap() : std::runtime_error("term_cap") {} };
Tree atom(char c) { return std::make_shared<Term>(Term{c, {}, {}, 1, 1}); }
class Parser {
    const std::string& text;
    bool iota;
    std::size_t pos = 0;
    void whitespace() {
        while (pos < text.size() && std::isspace(static_cast<unsigned char>(text[pos]))) ++pos;
    }
    Tree term(unsigned depth) {
        if (depth > 256) throw std::invalid_argument("source depth limit");
        whitespace();
        if (pos == text.size()) throw std::invalid_argument("missing term");
        char c = text[pos++];
        if (c == '(') {
            auto left = term(depth + 1), right = term(depth + 1);
            whitespace();
            if (pos == text.size() || text[pos++] != ')')
                throw std::invalid_argument("missing closing parenthesis");
            return application(left, right, 100000);
        }
        if ((iota && c == 'i') || (!iota && std::string("SKIxyzf").find(c) != std::string::npos))
            return atom(c);
        throw std::invalid_argument("invalid source atom");
    }
public:
    Parser(const std::string& s, bool only) : text(s), iota(only) {}
    Tree parse() {
        auto result = term(1); whitespace();
        if (pos != text.size()) throw std::invalid_argument("trailing term data");
        return result;
    }
};
bool is_atom(const Tree& t, char c) { return t && t->atom == c; }
bool redex(const Tree& t) {
    if (t->atom) return false;
    if (is_atom(t->left, 'I')) return true;
    if (!t->left->atom && is_atom(t->left->left, 'K')) return true;
    return !t->left->atom && !t->left->left->atom && is_atom(t->left->left->left, 'S');
}
bool reducible(const Tree& t) {
    return !t->atom && (redex(t) || reducible(t->left) || reducible(t->right));
}
// Return null only when the entire subtree is in full normal form.
Tree reduce_once(const Tree& t, std::uint64_t cap) {
    if (t->atom) return {};
    if (is_atom(t->left, 'I')) return t->right;
    if (!t->left->atom && is_atom(t->left->left, 'K')) return t->left->right;
    if (!t->left->atom && !t->left->left->atom && is_atom(t->left->left->left, 'S')) {
        auto x = t->left->left->right, y = t->left->right, z = t->right;
        return application(application(x, z, cap), application(y, z, cap), cap);
    }
    if (auto left = reduce_once(t->left, cap)) return application(left, t->right, cap);
    if (auto right = reduce_once(t->right, cap)) return application(t->left, right, cap);
    return {};
}
}
Tree application(Tree left, Tree right, std::uint64_t cap) {
    if (!left || !right) throw std::invalid_argument("null term");
    if (left->size >= cap || right->size > cap - left->size - 1) throw TermCap();
    auto depth = 1 + std::max(left->depth, right->depth);
    if (depth > 256) throw TermCap();
    return std::make_shared<Term>(Term{0, left, right, left->size + right->size + 1, depth});
}
Tree parse_term(const std::string& source, bool iota_only) {
    if (source.size() > 1024 * 1024) throw std::invalid_argument("source byte limit");
    return Parser(source, iota_only).parse();
}
Tree translate_iota(const Tree& source, std::uint64_t cap) {
    if (source->atom) {
        if (source->atom != 'i') throw std::invalid_argument("not a pure iota source");
        auto s = atom('S'), k = atom('K'), i = atom('I');
        return application(application(s, application(application(s, i, cap),
                           application(k, s, cap), cap), cap), application(k, k, cap), cap);
    }
    return application(translate_iota(source->left, cap), translate_iota(source->right, cap), cap);
}
Evaluation evaluate(Tree term, std::uint64_t max_steps, std::uint64_t max_nodes) {
    if (!term || max_nodes == 0 || max_nodes > 100000 || max_steps > 100000)
        throw std::invalid_argument("invalid reference evaluation budget");
    if (term->size > max_nodes) return {term, 0, "term_cap"};
    for (std::uint64_t steps = 0;; ++steps) {
        if (!reducible(term)) return {term, steps, "normal_form"};
        if (steps == max_steps) return {term, steps, "event_cap"};
        try {
            auto next = reduce_once(term, max_nodes);
            term = std::move(next);
        } catch (const TermCap&) {
            return {term, steps, "term_cap"};
        }
    }
}
std::string print_term(const Tree& t) {
    if (t->atom) return std::string(1, t->atom);
    return '(' + print_term(t->left) + ' ' + print_term(t->right) + ')';
}
}
