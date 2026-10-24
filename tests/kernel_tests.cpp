#include "minimal_universe/graph.hpp"
#include "minimal_universe/ski.hpp"
#include <iostream>
#include <stdexcept>

void check(bool value) { if (!value) throw std::runtime_error("test failed"); }
template<class F> void rejects(F f) {
    bool caught = false; try { f(); } catch (const std::exception&) { caught = true; }
    check(caught);
}
mu::Config config() {
    mu::Config c; c.nodes = 2; c.seed = {{0, 0}, {0, 0}};
    c.rule = {{0, 2}, {1, 0}, {2, 1}}; c.scheduler = "uniform"; c.rng = 17;
    return c;
}
int main() {
    try {
        auto c = config(); mu::Graph graph(c);
        check(graph.advance() == "applied");
        check(graph.nodes() == 3 && graph.edges().size() == 4);
        auto checkpoint = graph.checkpoint();
        check(mu::Graph::restore(checkpoint).checkpoint() == checkpoint);
        rejects([&] { mu::Graph::restore(checkpoint + "garbage"); });
        rejects([&] { mu::Graph::restore(checkpoint.substr(0, checkpoint.size()-1)); });
        auto corrupt = checkpoint; corrupt[14] = '9';
        rejects([&] { mu::Graph::restore(corrupt); });
        corrupt = checkpoint; corrupt.back() = 'x';
        rejects([&] { mu::Graph::restore(corrupt); });
        auto resumed = mu::Graph::restore(checkpoint);
        check(graph.run() == resumed.run());
        check(graph.checkpoint() == resumed.checkpoint());
        for (std::string cap : {"event_cap", "node_cap", "edge_cap"}) {
            auto limited = config();
            if (cap == "event_cap") limited.limits.events = 0;
            if (cap == "node_cap") limited.limits.nodes = 2;
            if (cap == "edge_cap") limited.limits.edges = 2;
            mu::Graph g(limited); auto before = g.checkpoint();
            check(g.advance() == cap); check(before == g.checkpoint());
            check(g.advance() == cap); check(before == g.checkpoint());
        }
        c.rule.clear(); mu::Graph deletion(c);
        check(deletion.run() == "no_eligible_edge");
        check(deletion.nodes() == 2 && deletion.events().size() == 2);
        rejects([] { mu::checked_add(mu::no_parent, 1); });
        check(mu::checked_add(mu::no_parent - 1, 1) == mu::no_parent);
        rejects([] { auto c = config(); c.seed = {{2, 0}}; mu::Graph g(c); });
        rejects([] { auto c = config(); c.rule = {{3, 0}}; mu::Graph g(c); });
        rejects([] { mu::parse_config("MU_CONFIG_1 -1"); });
        rejects([&] { mu::parse_config(mu::config_text(c) + "extra"); });
        mu::U64 rng = 0;
        check(mu::random_word(rng) == 0xe220a8397b1dcdafULL);
        rejects([&] { mu::uniform_index(rng, 0); });
        auto eval = [](std::string t) { return mu::evaluate(mu::parse_term(t), 100, 10000); };
        check(mu::print_term(eval("(I x)").term) == "x");
        check(mu::print_term(eval("((K x) ((S I) I))").term) == "x");
        check(mu::print_term(eval("(((S x) y) z)").term) == "((x z) (y z))");
        check(mu::print_term(eval("(x (I y))").term) == "(x y)");
        auto diverges = eval("(((S I) I) ((S I) I))");
        check(diverges.status == "event_cap" && diverges.steps == 100);
        auto t = mu::parse_term("(((S x) y) ((f x) y))");
        auto limited = mu::evaluate(t, 10, t->size);
        check(limited.status == "term_cap" && limited.steps == 0 && limited.term == t);
        check(mu::evaluate(mu::parse_term("x"), 0, 1).status == "normal_form");
        check(mu::evaluate(mu::parse_term("(I x)"), 0, 3).status == "event_cap");
        rejects([] { mu::parse_term("(i x)", true); });
        rejects([] { mu::parse_term("(I x) trailing"); });
        rejects([] { mu::parse_term("(I)"); });
        std::cout << "PASS: native graph, checkpoint, RNG, overflow, SKI, and cap fixtures\n";
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
