#include "kernel.hpp"
#include <chrono>
#include <iostream>
#include <stdexcept>
using namespace mu::g2assay;
using Clock=std::chrono::steady_clock;
int main(){
    try{
        U count=read_uint(std::cin);double evolution=0,checkpoint=0;
        for(U i=0;i<count;++i){
            auto config=read_config(std::cin);std::array<U,4> patch;
            for(auto& v:patch)v=read_uint(std::cin);
            U orientation=read_uint(std::cin),seed=read_uint(std::cin);
            Graph graph(config);graph.rewire(patch,orientation,seed);
            auto start=Clock::now();
            auto initial=Graph::restore(graph.checkpoint());
            if(initial.snapshot()!=graph.snapshot())throw std::runtime_error("initial checkpoint mismatch");
            checkpoint+=std::chrono::duration<double>(Clock::now()-start).count();
            start=Clock::now();auto status=graph.run();
            const double case_seconds=std::chrono::duration<double>(Clock::now()-start).count();
            if(case_seconds>5)throw std::runtime_error("native case deadline");
            evolution+=case_seconds;
            start=Clock::now();auto restored=Graph::restore(graph.checkpoint());
            if(restored.snapshot()!=graph.snapshot())throw std::runtime_error("final checkpoint mismatch");
            checkpoint+=std::chrono::duration<double>(Clock::now()-start).count();
            std::cout<<graph.json(status)<<'\n';
        }
        std::cin>>std::ws;if(!std::cin.eof())throw std::runtime_error("trailing input");
        std::cerr<<"{\"native_evolution_seconds\":"<<evolution<<",\"native_checkpoint_seconds\":"<<checkpoint<<"}\n";
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
