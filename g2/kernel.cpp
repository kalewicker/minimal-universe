#include "kernel.hpp"
#include <algorithm>
#include <cctype>
#include <new>
#include <sstream>
#include <stdexcept>

namespace mu::g2 {
namespace {
void demand(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
void token(std::istream& in, const char* expected) {
    std::string value; in >> value; demand(value==expected, "invalid format tag");
}
U word(U& state) {
    U z = (state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
void number(std::ostream& out,U n) { if(n==none) out<<"null"; else out<<n; }
void edge_json(std::ostream& out,const Edge& e) {
    out<<'['<<e.id<<','<<e.source<<','<<e.target<<','; number(out,e.producer); out<<']';
}
}
U checked_add(U a,U b) {
    if(b>none-a) throw std::overflow_error("counter overflow");
    return a+b;
}
U uniform_index(U& state,U bound) {
    demand(bound>0,"empty uniform sample");
    const U threshold=(U(0)-bound)%bound;
    for (;;) { U x=word(state); if (x>=threshold) return x%bound; }
}
U read_uint(std::istream& in) {
    std::string s; demand(bool(in>>s),"missing integer");
    demand(!s.empty() && std::all_of(s.begin(),s.end(),[](unsigned char c){return std::isdigit(c);}),
           "invalid unsigned integer");
    std::size_t end=0; U value=std::stoull(s,&end); demand(end==s.size(),"integer suffix");
    return value;
}
Config read_config(std::istream& in) {
    token(in,"MU_G2_CONFIG_1"); Config c;
    c.nodes=read_uint(in); c.rng=read_uint(in); in>>c.scheduler;
    c.limits={read_uint(in),read_uint(in),read_uint(in),read_uint(in)};
    U k=read_uint(in); demand(k<=3,"RHS too large");
    for(U i=0;i<k;++i) c.rhs.push_back({read_uint(in),read_uint(in)});
    U n=read_uint(in); demand(n<=256,"seed too large");
    for(U i=0;i<n;++i) c.seed.push_back({read_uint(in),read_uint(in)});
    return c;
}
std::string config_text(const Config& c) {
    std::ostringstream out;
    out<<"MU_G2_CONFIG_1\n"<<c.nodes<<' '<<c.rng<<' '<<c.scheduler<<'\n'
       <<c.limits.events<<' '<<c.limits.nodes<<' '<<c.limits.edges<<' '<<c.limits.matches<<'\n'
       <<c.rhs.size()<<'\n';
    for(auto a:c.rhs) out<<a[0]<<' '<<a[1]<<'\n';
    out<<c.seed.size()<<'\n'; for(auto a:c.seed) out<<a[0]<<' '<<a[1]<<'\n';
    return out.str();
}
Graph::Graph(Config c):config_(std::move(c)),nodes_(config_.nodes),next_(config_.seed.size()),rng_(config_.rng) {
    demand(config_.scheduler=="lex_first" || config_.scheduler=="lex_last" ||
           config_.scheduler=="uniform_match","invalid scheduler");
    demand(config_.limits.events<=128 && config_.limits.nodes<=256 && config_.limits.edges<=256 &&
           config_.limits.matches<=65536,"reference ceiling exceeded");
    demand(nodes_<=config_.limits.nodes && config_.seed.size()<=config_.limits.edges,"seed exceeds caps");
    demand(config_.rhs.size()<=3 && std::is_sorted(config_.rhs.begin(),config_.rhs.end()),"noncanonical RHS");
    for(auto a:config_.rhs) demand(a[0]<4 && a[1]<4,"invalid RHS symbol");
    for(auto a:config_.seed) {
        demand(a[0]<nodes_ && a[1]<nodes_,"invalid seed endpoint");
        edges_.push_back({static_cast<U>(edges_.size()),a[0],a[1],none});
    }
}
std::vector<std::pair<U,U>> Graph::matches() const {
    // Adjacency join, independently checked against Python occurrence-pair enumeration.
    std::vector<std::vector<U>> outgoing(nodes_);
    for(U i=0;i<edges_.size();++i) outgoing[edges_[i].source].push_back(i);
    std::vector<std::pair<U,U>> result;
    for(U i=0;i<edges_.size();++i)
        for(U j:outgoing[edges_[i].target]) if(i!=j) result.emplace_back(edges_[i].id,edges_[j].id);
    return result;
}
std::string Graph::advance(int fault) {
    // Count without materializing a possibly over-budget match set.
    std::vector<U> incoming(nodes_),outgoing(nodes_);
    U loops=0, count=0;
    for(const auto& e:edges_) { ++incoming[e.target]; ++outgoing[e.source]; loops+=e.source==e.target; }
    for(U v=0;v<nodes_;++v) count+=incoming[v]*outgoing[v];
    count-=loops;
    if(!count) return "no_eligible_match";
    if(events_.size()>=config_.limits.events) return "event_cap";
    const bool fresh=std::any_of(config_.rhs.begin(),config_.rhs.end(),[](Arc a){return a[0]==3 || a[1]==3;});
    U new_nodes=checked_add(nodes_,fresh);
    U new_size=checked_add(edges_.size()-2,config_.rhs.size());
    U new_next=checked_add(next_,config_.rhs.size());
    if(new_nodes>config_.limits.nodes) return "node_cap";
    if(new_size>config_.limits.edges) return "edge_cap";
    if(count>config_.limits.matches) return "match_cap";
    auto eligible=matches(); demand(eligible.size()==count,"internal match count mismatch");
    U rng=rng_, index=0;
    if(config_.scheduler=="lex_last") index=count-1;
    if(config_.scheduler=="uniform_match") index=uniform_index(rng,count);
    auto [a_id,b_id]=eligible.at(index);
    auto by_id=[](const Edge& e,U id){return e.id<id;};
    Edge a=*std::lower_bound(edges_.begin(),edges_.end(),a_id,by_id);
    Edge b=*std::lower_bound(edges_.begin(),edges_.end(),b_id,by_id);
    std::array<U,4> bind{a.source,a.target,b.target,nodes_};
    std::vector<Edge> next_edges; next_edges.reserve(new_size);
    for(const auto& e:edges_) if(e.id!=a.id && e.id!=b.id) next_edges.push_back(e);
    for(U i=0;i<config_.rhs.size();++i) {
        auto arc=config_.rhs[i];
        next_edges.push_back({next_+i,bind[arc[0]],bind[arc[1]],static_cast<U>(events_.size())});
    }
    if(fault==1) throw std::bad_alloc();
    std::vector<U> parents;
    if(a.producer!=none) parents.push_back(a.producer);
    if(b.producer!=none) parents.push_back(b.producer);
    std::sort(parents.begin(),parents.end()); parents.erase(std::unique(parents.begin(),parents.end()),parents.end());
    auto history=events_;
    history.push_back({static_cast<U>(events_.size()),a,b,{bind[0],bind[1],bind[2]},parents,
                       fresh?nodes_:none,next_,static_cast<U>(config_.rhs.size()),rng});
    if(fault==2) throw std::bad_alloc();
    edges_.swap(next_edges); events_.swap(history); nodes_=new_nodes;next_=new_next;rng_=rng;
    return "applied";
}
std::string Graph::prefix(U n) {
    demand(n<=128,"prefix ceiling");
    while(events_.size()<n) { auto status=advance(); if(status!="applied") return status; }
    return "checkpoint";
}
std::string Graph::run() { for(;;) { auto status=advance(); if(status!="applied") return status; } }
std::string Graph::json(const std::string& status) const {
    std::ostringstream out;
    out<<"{\"status\":\""<<status<<"\",\"nodes\":"<<nodes_<<",\"next_edge\":"<<next_
       <<",\"rng\":"<<rng_<<",\"scheduler\":\""<<config_.scheduler<<"\",\"edges\":[";
    bool first=true; for(const auto& e:edges_) { if(!first) out<<',';first=false;edge_json(out,e); }
    out<<"],\"events\":[";first=true;
    for(const auto& e:events_) {
        if(!first)out<<',';first=false;
        out<<"{\"id\":"<<e.id<<",\"consumed\":[";edge_json(out,e.a);out<<',';edge_json(out,e.b);
        out<<"],\"binding\":["<<e.binding[0]<<','<<e.binding[1]<<','<<e.binding[2]<<"],\"parents\":[";
        for(std::size_t i=0;i<e.parents.size();++i){if(i)out<<',';out<<e.parents[i];}
        out<<"],\"fresh\":";number(out,e.fresh);
        out<<",\"first_output\":"<<e.first<<",\"output_count\":"<<e.count
           <<",\"scheduler\":\""<<config_.scheduler<<"\",\"rng\":"<<e.rng<<'}';
    }
    out<<"]}";return out.str();
}
std::string Graph::snapshot() const { return json("checkpoint"); }
std::string Graph::checkpoint() const {
    std::ostringstream out;
    out<<"MU_G2_CHECKPOINT_1\n"<<config_text(config_)<<"PREFIX "<<events_.size()<<'\n'<<snapshot()<<'\n';
    return out.str();
}
Graph Graph::restore(const std::string& text) {
    demand(text.size()<=4194304,"checkpoint too large");
    std::istringstream in(text);token(in,"MU_G2_CHECKPOINT_1");auto c=read_config(in);
    token(in,"PREFIX");U n=read_uint(in);demand(n<=128,"checkpoint prefix too large");
    demand(in.get()=='\n',"checkpoint separator");
    std::string stored((std::istreambuf_iterator<char>(in)),std::istreambuf_iterator<char>());
    Graph graph(c); for(U i=0;i<n;++i) demand(graph.advance()=="applied","checkpoint replay stopped");
    demand(stored==graph.snapshot()+"\n","checkpoint replay mismatch");
    return graph;
}
}
