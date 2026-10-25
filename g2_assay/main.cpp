#include "kernel.hpp"
#include <iostream>
#include <stdexcept>
using namespace mu::g2assay;
int main() {
    try {
        U count=read_uint(std::cin);
        for(U i=0;i<count;++i) {
            auto config=read_config(std::cin);
            U pre=read_uint(std::cin), ori=read_uint(std::cin), seed=read_uint(std::cin);
            Graph graph(config); graph.prefix(pre);
            const auto before=graph.checkpoint();
            for(int fault:{1,2}) {
                bool rejected=false;
                try{graph.rewire({0,1,2,3},ori,seed,fault);}catch(const std::bad_alloc&){rejected=true;}
                if(!rejected || graph.checkpoint()!=before)throw std::runtime_error("atomic fault failure");
            }
            for(auto patch:{std::array<U,4>{0,0,2,3},std::array<U,4>{0,1,2,config.nodes}}) {
                bool rejected=false;
                try{graph.rewire(patch,ori,seed);}catch(const std::runtime_error&){rejected=true;}
                if(!rejected || graph.checkpoint()!=before)throw std::runtime_error("invalid patch mutation");
            }
            for(U bad:{U(4),none}) {
                bool rejected=false;
                try{graph.rewire({0,1,2,3},bad,seed);}catch(const std::runtime_error&){rejected=true;}
                if(!rejected || graph.checkpoint()!=before)throw std::runtime_error("orientation mutation");
            }
            for(int kind:{0,1,2}) {
                auto invalid=config;
                if(kind==1)invalid.seed.push_back({0,1});
                if(kind==2)invalid.seed.push_back({0,0});
                // Missing-dyad fixture always removes its first internal occurrence.
                if(kind==0){invalid=config;invalid.seed.erase(invalid.seed.begin());}
                Graph bad(invalid);const auto frozen=bad.checkpoint();bool rejected=false;
                try{bad.rewire({0,1,2,3},ori,seed);}catch(const std::runtime_error&){rejected=true;}
                if(!rejected || bad.checkpoint()!=frozen)throw std::runtime_error("induced patch mutation");
            }
            graph.rewire({0,1,2,3},ori,seed);
            const auto initial=graph.checkpoint();
            bool rejected=false;
            try{graph.rewire({0,1,2,3},ori,seed);}catch(const std::runtime_error&){rejected=true;}
            if(!rejected || graph.checkpoint()!=initial)throw std::runtime_error("repeat mutation");
            rejected=false;
            try{Graph::restore(initial+" ");}catch(const std::runtime_error&){rejected=true;}
            if(!rejected)throw std::runtime_error("tamper accepted");
            auto restored=Graph::restore(initial);
            auto status=graph.run(), other=restored.run();
            if(status!=other || graph.checkpoint()!=restored.checkpoint())throw std::runtime_error("resume mismatch");
            auto final=Graph::restore(graph.checkpoint());
            if(final.snapshot()!=graph.snapshot())throw std::runtime_error("final replay mismatch");
            std::cout<<graph.json(status)<<'\n';
        }
        std::cin>>std::ws;
        if(!std::cin.eof())throw std::runtime_error("trailing input");
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
