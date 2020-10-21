#include <iostream>
#include <fstream>
#include <iterator>
#include <algorithm>
#include <vector>
#include <string>
#include <boost/algorithm/string.hpp>
#include "utils/FileReader.h"
#include "indices/ZM.h"
#include "indices/RSMI.h"
#include "utils/ExpRecorder.h"
#include "utils/Constants.h"
#include "utils/FileWriter.h"

#include <torch/torch.h>

#include <xmmintrin.h>
#include <stdlib.h>
#include <stdio.h>
#include <getopt.h>

using namespace std;

#ifndef use_gpu
#define use_gpu
// check kNN_query
// struct sortD
// {
//     bool operator()(double d1, double d2)
//     {
//         return d1 < d2;
//     }
// };

// void check(vector<Point*> points)
// {
//      vector<double> dists;
//     for (Point *point : points)
//     {
//         dists.push_back(point->cal_dist(points[0]));
//     }
//     sort(dists.begin(), dists.end(), sortD());
//     for (int i = 0; i < 10; i++)
//     {
//         cout << dists[i] << endl;
//     }
// }

int ks[] = {1, 5, 25, 125, 625};
float areas[] = {0.000006, 0.000025, 0.0001, 0.0004, 0.0016};
float ratios[] = {0.25, 0.5, 1, 2, 4};
int Ns[] = {5000, 2500, 500};

// double ks[] = {125};
// double areas[] = {0.0016};
// double ratios[] = {1};

int k_length = sizeof(ks) / sizeof(ks[0]);
int window_length = sizeof(areas) / sizeof(areas[0]);
int ratio_length = sizeof(ratios) / sizeof(ratios[0]);

int n_length = sizeof(Ns) / sizeof(Ns[0]);

// int query_window_num = 1000;
int query_window_num = 1000;
int query_k_num = 1000;

long long cardinality = 10000;
long long inserted_num = cardinality / 10;
string distribution = Constants::DEFAULT_DISTRIBUTION;
int inserted_partition = 5;
int skewness = 1;

double knn_diff(vector<Point> acc, vector<Point> pred)
{
    int num = 0;
    for (Point point : pred)
    {
        for (Point point1 : acc)
        {
            if (point.x == point1.x && point.y == point1.y)
            {
                num++;
            }
        }
    }
    return num * 1.0 / pred.size();
}

void expRSMI(FileWriter file_writer, ExpRecorder exp_recorder, vector<Point> points, map<string, vector<Mbr>> mbrs_map, vector<Point> query_poitns, vector<Point> insert_points, string model_path)
{
    exp_recorder.clean();
    exp_recorder.structure_name = "RSMI";
    cout << "expRSMI" << endl;
    // RSMI rsmi(4, 10000);
    // rsmi.build(exp_recorder, points);
    int level = 0;
    int max_width = Constants::MAX_WIDTH;
    RSMI::model_path_root = model_path;
    RSMI *partition = new RSMI(level, max_width);
    auto start = chrono::high_resolution_clock::now();
    partition->model_path = model_path;
    partition->build(exp_recorder, points);
    // cout<< "RSMI::total_num: " << RSMI::total_num << endl;
    // cout << "finish point_query max_error: " << exp_recorder.max_error << endl;
    // cout << "finish point_query min_error: " << exp_recorder.min_error << endl;
    // cout << "finish point_query average_max_error: " << exp_recorder.average_max_error << endl;
    // cout << "finish point_query average_min_error: " << exp_recorder.average_min_error << endl;
    // cout << "last_level_model_num: " << exp_recorder.last_level_model_num << endl;
    // cout << "leaf_node_num: " << exp_recorder.leaf_node_num << endl;
    // cout << "non_leaf_node_num: " << exp_recorder.non_leaf_node_num << endl;
    // cout << "depth: " << exp_recorder.depth << endl;
    auto finish = chrono::high_resolution_clock::now();
    exp_recorder.time = chrono::duration_cast<chrono::nanoseconds>(finish - start).count();
    cout << "build time: " << exp_recorder.time << endl;
    exp_recorder.size = (2 * Constants::HIDDEN_LAYER_WIDTH + Constants::HIDDEN_LAYER_WIDTH * 1 + Constants::HIDDEN_LAYER_WIDTH * 1 + 1) * Constants::EACH_DIM_LENGTH * exp_recorder.non_leaf_node_num + (Constants::DIM * Constants::PAGESIZE + Constants::PAGESIZE + Constants::DIM * Constants::DIM) * Constants::EACH_DIM_LENGTH * exp_recorder.leaf_node_num;
    file_writer.write_build(exp_recorder);
    exp_recorder.clean();
    partition->point_query(exp_recorder, points);
    file_writer.write_point_query(exp_recorder);
    exp_recorder.clean();

    exp_recorder.window_size = areas[2];
    exp_recorder.window_ratio = ratios[2];
    partition->acc_window_query(exp_recorder, mbrs_map[to_string(areas[2]) + to_string(ratios[2])]);
    cout<< "exp_recorder.acc_window_query_qesult_size: " << exp_recorder.acc_window_query_qesult_size << endl;
    file_writer.write_acc_window_query(exp_recorder);
    partition->window_query(exp_recorder, mbrs_map[to_string(areas[2]) + to_string(ratios[2])]);
    exp_recorder.accuracy = ((double)exp_recorder.window_query_result_size) / exp_recorder.acc_window_query_qesult_size;
    file_writer.write_window_query(exp_recorder);
    cout<< "exp_recorder.window_query_result_size: " << exp_recorder.window_query_result_size << endl;
    cout<< "exp_recorder.accuracy: " << exp_recorder.accuracy << endl;

    exp_recorder.clean();
    exp_recorder.k_num = ks[2];
    partition->acc_kNN_query(exp_recorder, query_poitns, ks[2]);
    file_writer.write_acc_kNN_query(exp_recorder);
    partition->kNN_query(exp_recorder, query_poitns, ks[2]);
    exp_recorder.accuracy = knn_diff(exp_recorder.acc_knn_query_results, exp_recorder.knn_query_results);
    cout<< "exp_recorder.knn_query_results: " << exp_recorder.knn_query_results.size() << endl;
    cout<< "exp_recorder.accuracy: " << exp_recorder.accuracy << endl;
    file_writer.write_kNN_query(exp_recorder);
    exp_recorder.clean();

    partition->insert(exp_recorder, insert_points);
    partition->point_query(exp_recorder, insert_points);

}
string RSMI::model_path_root = "";
// int RSMI::total_num = 0;
int main(int argc, char **argv)
{

    int c;
    static struct option long_options[] =
    {
        {"cardinality", required_argument,NULL,'c'},
        {"distribution",required_argument,      NULL,'d'},
        {"skewness", required_argument,      NULL,'s'}
    };

    //循环执行，确保所有选项都能得到处理
    while(1)
    {
        int opt_index = 0;
        //参数解析方法，重点
        c = getopt_long(argc, argv,"c:d:s:", long_options,&opt_index);
        
        if(-1 == c)
        {
            break;
        }
        //根据返回值做出相应处理
        switch(c)
        {
            case 'c':
                cardinality = atoll(optarg);
                break;
            case 'd':
                distribution = optarg;
                break;
            case 's':
                skewness = atoi(optarg);
                break;
        }
    }
    // cardinality = atoll(argv[1]);
    // distribution = argv[2];
    // skewness = atoi(argv[3]);

    ExpRecorder exp_recorder;
    exp_recorder.dataset_cardinality = cardinality;
    exp_recorder.distribution = distribution;
    exp_recorder.skewness = skewness;
    inserted_num = cardinality / 2;

    // // exp_recorder.window_size = area;
    // // exp_recorder.window_ratio = ratio;
    FileReader filereader((Constants::DATASETS + exp_recorder.distribution + "_" + to_string(exp_recorder.dataset_cardinality) + "_" + to_string(exp_recorder.skewness) + "_2_.csv"), ",");
    vector<Point> points = filereader.get_points();
    exp_recorder.insert_num = inserted_num;
    vector<Point> query_poitns;
    vector<Point> insert_points;
    /***********************write query data*********************/
    FileWriter query_file_writer(Constants::QUERYPROFILES);
    query_poitns = Point::get_points(points, query_k_num);
    query_file_writer.write_points(query_poitns, exp_recorder);

    insert_points = Point::get_inserted_points(exp_recorder.insert_num);
    query_file_writer.write_inserted_points(insert_points, exp_recorder);

    for (size_t i = 0; i < window_length; i++)
    {
        for (size_t j = 0; j < ratio_length; j++)
        {
            exp_recorder.window_size = areas[i];
            exp_recorder.window_ratio = ratios[j];
            vector<Mbr> mbrs = Mbr::get_mbrs(points, exp_recorder.window_size, query_window_num, exp_recorder.window_ratio);
            query_file_writer.write_mbrs(mbrs, exp_recorder);
        }
    }

    /********************************************/

    FileReader knn_reader((Constants::QUERYPROFILES + "knn/" + exp_recorder.distribution + "_" + to_string(exp_recorder.dataset_cardinality) + "_" + to_string(exp_recorder.k_num) + ".csv"), ",");
    map<string, vector<Mbr>> mbrs_map;
    FileReader query_filereader;

    query_poitns = query_filereader.get_points((Constants::QUERYPROFILES + Constants::KNN + exp_recorder.distribution + "_" + to_string(exp_recorder.dataset_cardinality) + "_" + to_string(exp_recorder.skewness) + ".csv"), ",");
    insert_points = query_filereader.get_points((Constants::QUERYPROFILES + Constants::UPDATE + exp_recorder.distribution + "_" + to_string(exp_recorder.dataset_cardinality) + "_" + to_string(exp_recorder.skewness) + "_" + to_string(exp_recorder.insert_num) + ".csv"), ",");

    for (size_t i = 0; i < window_length; i++)
    {
        for (size_t j = 0; j < ratio_length; j++)
        {
            exp_recorder.window_size = areas[i];
            exp_recorder.window_ratio = ratios[j];
            vector<Mbr> mbrs = query_filereader.get_mbrs((Constants::QUERYPROFILES + Constants::WINDOW + exp_recorder.distribution + "_" + to_string(exp_recorder.dataset_cardinality) + "_" + to_string(exp_recorder.skewness) + "_" + to_string(exp_recorder.window_size) + "_" + to_string(exp_recorder.window_ratio) + ".csv"), ",");
            mbrs_map.insert(pair<string, vector<Mbr>>(to_string(areas[i]) + to_string(ratios[j]), mbrs));
        }
    }
    string model_path = "./torch_models/" + distribution + "_" + to_string(cardinality) + "/";
    FileWriter file_writer(Constants::RECORDS);
    // // expZM(file_writer, exp_recorder, points, mbrs_map, query_poitns, insert_points);
    expRSMI(file_writer, exp_recorder, points, mbrs_map, query_poitns, insert_points, model_path);
}
#endif  // use_gpu