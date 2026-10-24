#include "kernel.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>

using namespace mu::g2;
namespace fs=std::filesystem;
namespace {
std::string read(const fs::path& path,U ceiling=4194304) {
    if(fs::file_size(path)>ceiling) throw std::runtime_error("input byte cap");
    std::ifstream in(path);if(!in)throw std::runtime_error("open input failed");
    return {std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>()};
}
void write(const fs::path& path,const std::string& data) {
    if(fs::exists(path))throw std::runtime_error("refusing output overwrite");
    std::ofstream out(path);out<<data;out.close();
    if(!out)throw std::runtime_error("checkpoint write failed");
}
void end(std::istream& in) { std::string extra;if(in>>extra)throw std::runtime_error("trailing input"); }
void match_json(const Graph& graph) {
    std::cout<<'[';bool first=true;
    for(auto [a,b]:graph.matches()) {if(!first)std::cout<<',';first=false;std::cout<<'['<<a<<','<<b<<']';}
    std::cout<<']';
}
}
int main(int argc,char** argv) {
    try {
        if(argc<3)throw std::runtime_error("usage: mu-g2 run CONFIG [CHECKPOINT PREFIX] | resume CHECKPOINT | batch INPUT CHECKPOINT_DIR PREFIX | resume-batch LIST");
        const std::string mode=argv[1];
        if(mode=="run" && (argc==3 || argc==5)) {
            std::istringstream in(read(argv[2]));Graph graph(read_config(in));end(in);
            if(argc==5) { std::istringstream number(argv[4]);U n=read_uint(number);end(number);graph.prefix(n);write(argv[3],graph.checkpoint()); }
            auto status=graph.run();std::cout<<graph.json(status)<<'\n';
        } else if(mode=="resume" && argc==3) {
            auto graph=Graph::restore(read(argv[2]));auto status=graph.run();std::cout<<graph.json(status)<<'\n';
        } else if(mode=="batch" && argc==5) {
            std::istringstream in(read(argv[2]));std::string tag;in>>tag;
            if(tag!="MU_G2_BATCH_1")throw std::runtime_error("invalid batch tag");
            U cases=read_uint(in);if(cases>20000)throw std::runtime_error("batch case cap");
            std::istringstream number(argv[4]);U split=read_uint(number);end(number);
            if(!fs::create_directory(argv[3]))throw std::runtime_error("checkpoint directory exists");
            for(U i=0;i<cases;++i) {
                Graph graph(read_config(in));std::cout<<"{\"index\":"<<i<<",\"initial_matches\":";match_json(graph);
                auto status=graph.prefix(split);std::cout<<",\"mid\":"<<graph.json(status);
                write(fs::path(argv[3])/(std::to_string(i)+".g2"),graph.checkpoint());
                status=graph.run();std::cout<<",\"final\":"<<graph.json(status)<<"}\n";
            }
            end(in);
        } else if(mode=="resume-batch" && argc==3) {
            std::istringstream in(read(argv[2]));U cases=read_uint(in);std::string path;std::getline(in,path);
            if(cases>20000)throw std::runtime_error("restore batch cap");
            for(U i=0;i<cases;++i) {
                if(!std::getline(in,path) || path.empty())throw std::runtime_error("missing checkpoint path");
                auto graph=Graph::restore(read(path));auto status=graph.run();
                std::cout<<"{\"index\":"<<i<<",\"final\":"<<graph.json(status)<<"}\n";
            }
            end(in);
        } else throw std::runtime_error("invalid arguments");
        return 0;
    } catch(const std::exception& e) {std::cerr<<"mu-g2: "<<e.what()<<'\n';return 1;}
}
