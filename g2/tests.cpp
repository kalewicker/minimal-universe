#include "kernel.hpp"
#include <functional>
#include <iostream>
#include <new>
#include <sstream>
#include <stdexcept>
using namespace mu::g2;
namespace {
void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
void rejects(const std::function<void()>& f){bool threw=false;try{f();}catch(const std::exception&){threw=true;}check(threw,"expected rejection");}
Config loops(){Config c;c.nodes=1;c.seed={{0,0},{0,0}};c.rhs={{0,0},{0,0},{0,0}};c.scheduler="uniform_match";return c;}
void unchanged(Config c,const std::string& status){Graph g(c);auto before=g.checkpoint();check(g.advance()==status,"wrong cap status");check(before==g.checkpoint(),"cap mutated state");}
}
int main(){
try{
    Config c=loops();
    Graph g(c);check(g.matches().size()==2,"parallel loops");
    check(g.advance()=="applied","first step");
    auto pairs=g.matches();check(pairs.front()==std::pair<U,U>{2,3},"stable occurrence IDs");
    auto checkpoint=g.checkpoint();auto restored=Graph::restore(checkpoint);
    auto s1=g.run(),s2=restored.run();check(g.json(s1)==restored.json(s2),"restore continuation");
    for(int fault:{1,2}){Graph f(c);auto before=f.checkpoint();rejects([&]{f.advance(fault);});check(before==f.checkpoint(),"allocation fault mutated state");check(f.advance()=="applied","fault retry not equivalent");}
    c.limits.events=0;unchanged(c,"event_cap");c=loops();c.limits.edges=2;unchanged(c,"edge_cap");
    c=loops();c.rhs={{0,3},{3,1}};c.limits.nodes=1;unchanged(c,"node_cap");
    c=loops();c.limits.matches=1;unchanged(c,"match_cap");
    c=loops();c.limits.matches=2;Graph exact(c);check(exact.advance()=="applied","exact match-cap boundary");
    c=loops();c.seed={{0,0}};c.limits.events=0;unchanged(c,"no_eligible_match");
    rejects([]{checked_add(none,1);});check(checked_add(none-1,1)==none,"checked-add boundary");
    U rng=3;check(uniform_index(rng,(U(1)<<63)+1)==3694763184872335752ULL &&
                 rng==4354685564936845357ULL,"uniform rejection continuation");
    rng=none;check(uniform_index(rng,1)==0 && rng==11400714819323198484ULL,"RNG wrap and singleton draw");
    rejects([&]{uniform_index(rng,0);});
    rejects([&]{auto bad=checkpoint;bad.back()='x';Graph::restore(bad);});
    rejects([&]{Graph::restore("MU_CHECKPOINT_1\n"+checkpoint);});
    rejects([&]{auto bad=checkpoint;bad.replace(bad.find("PREFIX "),9,"PREFIX 99");Graph::restore(bad);});
    rejects([&]{Graph::restore(checkpoint+"junk");});
    rejects([]{std::istringstream in("-1");read_uint(in);});
    rejects([]{std::istringstream in("18446744073709551616");read_uint(in);});
    rejects([]{Config bad=loops();bad.scheduler="uniform";Graph rejected(bad);});
    rejects([]{Config bad=loops();bad.rhs={{3,0},{0,0}};Graph rejected(bad);});
    rejects([]{Config bad=loops();bad.seed={{0,1}};Graph rejected(bad);});
    Config overlap;overlap.nodes=3;overlap.seed={{0,0},{0,1},{1,2}};
    Graph left(overlap);overlap.scheduler="lex_last";Graph right(overlap);
    check(left.run()=="no_eligible_match" && right.run()=="no_eligible_match","witness terminal");
    check(left.json("terminal")!=right.json("terminal"),"witness branches");
    c=loops();c.scheduler="lex_first";Graph merge(c);merge.run();
    check(merge.json("done").find("\"parents\":[0,1]")!=std::string::npos,"two-producer ancestry");
    std::cout<<"G2 kernel checks passed\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
