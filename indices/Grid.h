#include <iostream>
#include <vector>
#include "../utils/SortTools.h"
#include "../entities/LeafNode.h"
#include "../entities/Bucket.h"
#include "../utils/ExpRecorder.h"
#include "../entities/Mbr.h"
#include "../entities/Point.h"
#include <queue>

using namespace std;

class Grid
{
private:
    int numXCells = 1;
    int numYCells = 1;
    float domainSize = 1.0;
    vector<vector<Bucket>> buckets;

    float xGap;
    float yGap;

public:
    Grid(int numXCells, int numYCells, float domainSize);
    Grid(int numXCells, int numYCells);
    ~Grid();

    void build(ExpRecorder &expRecorder, vector<Point> points);

    void pointQuery(ExpRecorder &expRecorder, Point queryPoint);
    void pointQuery(ExpRecorder &expRecorder, vector<Point> queryPoints);

    void windowQuery(ExpRecorder &expRecorder, vector<Mbr> queryWindows);
    vector<Point> windowQuery(ExpRecorder &expRecorder, Mbr queryWindow);

    void kNNQuery(ExpRecorder &expRecorder, vector<Point> queryPoints, int k);
    vector<Point> kNNQuery(ExpRecorder &expRecorder, Point queryPoint, int k);

    void insert(ExpRecorder &expRecorder, Point);
    void insert(ExpRecorder &expRecorder, vector<Point>);

    void remove(ExpRecorder &expRecorder, Point);
    void remove(ExpRecorder &expRecorder, vector<Point>);
};

Grid::Grid(int numXCells, int numYCells, float domainSize)
{
    this->numXCells = numXCells;
    this->numYCells = numYCells;
    this->domainSize = domainSize;
    xGap = domainSize / numXCells;
    yGap = domainSize / numYCells;
}

Grid::Grid(int numXCells, int numYCells)
{
    this->numXCells = numXCells;
    this->numYCells = numYCells;
    xGap = domainSize / numXCells;
    yGap = domainSize / numYCells;
}

Grid::~Grid()
{
}

void Grid::build(ExpRecorder &expRecorder, vector<Point> points)
{
    cout << "build:" << endl;
    // initialize initial structure
    auto start = chrono::high_resolution_clock::now();
    cout << "numXCells:" << numXCells << endl;
    cout << "numYCells:" << numYCells << endl;
    for (size_t i = 0; i < numXCells; i++)
    {
        vector<Bucket> vec;
        for (size_t j = 0; j < numYCells; j++)
        {
            Mbr tMbr(i * xGap, j * yGap, (i + 1) * xGap, (j + 1) * yGap);
            Bucket bucket(tMbr);
            expRecorder.leaf_node_num++;
            expRecorder.leaf_node_num++;
            vec.push_back(bucket);
            // cout << "i: " << i << " j: " << j << endl;
        }
        buckets.push_back(vec);
    }

    for (Point point : points)
    {
        int xIndex = (int)(point.x / xGap);
        int yIndex = (int)(point.y / yGap);
        xIndex = xIndex < 0 ? 0 : xIndex;
        xIndex = xIndex >= numXCells ? numXCells - 1 : xIndex;
        yIndex = yIndex < 0 ? 0 : yIndex;
        yIndex = yIndex >= numYCells ? numYCells - 1 : yIndex;
        if (buckets[xIndex][yIndex].insert(point))
        {
            expRecorder.leaf_node_num++;
        }
    }
    auto finish = chrono::high_resolution_clock::now();
    expRecorder.time = chrono::duration_cast<chrono::nanoseconds>(finish - start).count();
    expRecorder.cal_size();
}

void Grid::pointQuery(ExpRecorder &expRecorder, Point point)
{
    int xIndex = (int)(point.x / xGap);
    int yIndex = (int)(point.y / yGap);
    xIndex = xIndex < 0 ? 0 : xIndex;
    xIndex = xIndex >= numXCells ? numXCells - 1 : xIndex;
    yIndex = yIndex < 0 ? 0 : yIndex;
    yIndex = yIndex >= numYCells ? numYCells - 1 : yIndex;
    // TODO finish Insert method
    if (!buckets[xIndex][yIndex].pointQuery(expRecorder, point))
    {
        // cout << "not found!" << endl;
    }
}

void Grid::pointQuery(ExpRecorder &expRecorder, vector<Point> queryPoints)
{
    cout << "Grid::pointQuery:" << endl;
    auto start = chrono::high_resolution_clock::now();
    for (Point point : queryPoints)
    {
        pointQuery(expRecorder, point);
    }
    auto finish = chrono::high_resolution_clock::now();
    expRecorder.time = chrono::duration_cast<chrono::nanoseconds>(finish - start).count() / queryPoints.size();
    expRecorder.page_access = (double)expRecorder.page_access / queryPoints.size();
}

void Grid::windowQuery(ExpRecorder &expRecorder, vector<Mbr> queryWindows)
{
    cout << "windowQuery:" << endl;
    long long time = 0;
    for (Mbr queryWindow : queryWindows)
    {
        auto start = chrono::high_resolution_clock::now();
        windowQuery(expRecorder, queryWindow);
        auto finish = chrono::high_resolution_clock::now();
        expRecorder.window_query_results.clear();
        expRecorder.window_query_results.shrink_to_fit();
        time += chrono::duration_cast<chrono::nanoseconds>(finish - start).count();
    }
    expRecorder.time = time / queryWindows.size();
    expRecorder.page_access = (double)expRecorder.page_access / queryWindows.size();
    cout<< "time: " << expRecorder.time << endl;
}

vector<Point> Grid::windowQuery(ExpRecorder &expRecorder, Mbr queryWindow)
{
    // vector<Point> points = queryWindow.getCornerPoints();
    // int lowerX = numXCells;
    // int upperX = 0;
    // int lowerY = numYCells;
    // int upperY = 0;

    // for (Point point : points)
    // {
    //     int xIndex = (int)(point.x / xGap);
    //     int yIndex = (int)(point.y / yGap);
    //     if (xIndex < lowerX)
    //     {
    //         lowerX = xIndex;
    //     }
    //     if (yIndex < lowerY)
    //     {
    //         lowerY = yIndex;
    //     }
    //     if (xIndex > upperX)
    //     {
    //         upperX = xIndex;
    //     }
    //     if (yIndex > upperY)
    //     {
    //         upperY = yIndex;
    //     }
    // }
    int lowerX = queryWindow.x1 / xGap;
    int lowerY = queryWindow.y1 / yGap;

    int upperX = queryWindow.x2 / xGap;
    int upperY = queryWindow.y2 / yGap;
    for (size_t i = lowerX; i <= upperX; i++)
    {
        for (size_t j = lowerY; j <= upperY; j++)
        {
            if (i ==lowerX || i == upperX || j == lowerY || j == upperY)
            {
                buckets[i][j].windowQuery(expRecorder, queryWindow);
            }
            else
            {
                expRecorder.window_query_results.insert(expRecorder.window_query_results.end(), buckets[i][j].dynArray.begin(), buckets[i][j].dynArray.end());
            }
        }
    }
    return expRecorder.window_query_results;
}

void Grid::kNNQuery(ExpRecorder &expRecorder, vector<Point> queryPoints, int k)
{
    cout << "kNNQuery:" << endl;
    auto start = chrono::high_resolution_clock::now();
    for (Point point : queryPoints)
    {
        kNNQuery(expRecorder, point, k);
    }
    auto finish = chrono::high_resolution_clock::now();
    expRecorder.time = chrono::duration_cast<chrono::nanoseconds>(finish - start).count() / queryPoints.size();
    expRecorder.page_access = (double)expRecorder.page_access / queryPoints.size();
}

vector<Point> Grid::kNNQuery(ExpRecorder &expRecorder, Point point, int k)
{
    // cout<< "Grid::kNNQuery single " << endl;
    vector<Point> result;
    int xIndex = (int)(point.x / xGap);
    int yIndex = (int)(point.y / yGap);
    int lowerX = xIndex;
    int upperX = xIndex;
    int lowerY = yIndex;
    int upperY = yIndex;
    while (true)
    {
        float sideX = (point.x - lowerX * xGap) < (upperX * xGap + xGap - point.x) ? (point.x - lowerX * xGap) : (upperX * xGap + xGap - point.x);
        sideX = lowerX == 0 ? (upperX * xGap + xGap - point.x) : sideX;
        sideX = upperX == numXCells - 1 ? (point.x - lowerX * xGap) : sideX;
        float sideY = (point.y - lowerY * yGap) < (upperY * yGap + yGap - point.y) ? (point.y - lowerY * yGap) : (upperY * yGap + yGap - point.y);
        sideY = lowerY == 0 ? (upperY * yGap + yGap - point.y) : sideY;
        sideY = upperY == numYCells - 1 ? (point.y - lowerY * yGap) : sideY;
        float side = sideX < sideY ? sideX : sideY;

        vector<Point> kNNQueryResults;
        for (size_t i = lowerX; i <= upperX; i++)
        {
            for (size_t j = lowerY; j <= upperY; j++)
            {
                expRecorder.page_access++;
                vector<Point> tempResult = buckets[i][j].getAllPoints();
                kNNQueryResults.insert(kNNQueryResults.end(), tempResult.begin(), tempResult.end());
            }
        }
        if (kNNQueryResults.size() >= k)
        {
            sort(kNNQueryResults.begin(), kNNQueryResults.end(), sortForKNN(point));
            Point last = kNNQueryResults[k - 1];
            if (last.cal_dist(point) <= side)
            {
                // TODO get top K from the vector.
                auto bn = kNNQueryResults.begin();
                auto en = kNNQueryResults.begin() + k;
                vector<Point> vec(bn, en);
                result = vec;
                break;
            }
        }

        lowerX--;
        lowerX = lowerX < 0 ? 0 : lowerX;
        upperX++;
        upperX = upperX >= numXCells ? numXCells - 1 : upperX;
        lowerY--;
        lowerY = lowerY < 0 ? 0 : lowerY;
        upperY++;
        upperY = upperY >= numYCells ? numYCells - 1 : upperY;
    }
    // cout<< "Grid::kNNQuery single finish" << endl;
    return result;
}

void Grid::insert(ExpRecorder &expRecorder, Point point)
{

    int xIndex = (int)(point.x / xGap);
    int yIndex = (int)(point.y / yGap);
    xIndex = xIndex < 0 ? 0 : xIndex;
    xIndex = xIndex >= numXCells ? numXCells - 1 : xIndex;
    yIndex = yIndex < 0 ? 0 : yIndex;
    yIndex = yIndex >= numYCells ? numYCells - 1 : yIndex;
    buckets[xIndex][yIndex].insert(point);
}

void Grid::insert(ExpRecorder &expRecorder, vector<Point> points)
{
    cout << "insert:" << endl;
    auto start = chrono::high_resolution_clock::now();
    for (Point point : points)
    {
        insert(expRecorder, point);
    }
    auto finish = chrono::high_resolution_clock::now();
    long long oldTimeCost = expRecorder.insert_time * expRecorder.insert_num;
    expRecorder.insert_num += points.size();
    expRecorder.insert_time = (oldTimeCost + chrono::duration_cast<chrono::nanoseconds>(finish - start).count()) / expRecorder.insert_num;
}

void Grid::remove(ExpRecorder &expRecorder, Point point)
{
    int xIndex = (int)(point.x / xGap);
    int yIndex = (int)(point.y / yGap);
    xIndex = xIndex < 0 ? 0 : xIndex;
    xIndex = xIndex >= numXCells ? numXCells - 1 : xIndex;
    yIndex = yIndex < 0 ? 0 : yIndex;
    yIndex = yIndex >= numYCells ? numYCells - 1 : yIndex;
    buckets[xIndex][yIndex].remove(point);
}

void Grid::remove(ExpRecorder &expRecorder, vector<Point> points)
{
    // cout << "remove:" << endl;
    auto start = chrono::high_resolution_clock::now();
    for (Point point : points)
    {
        remove(expRecorder, point);
    }
    auto finish = chrono::high_resolution_clock::now();
    // cout << "end:" << end.tv_nsec << " begin" << begin.tv_nsec << endl;
    long long oldTimeCost = expRecorder.delete_time * expRecorder.delete_num;
    expRecorder.delete_num += points.size();
    expRecorder.delete_time = (oldTimeCost + chrono::duration_cast<chrono::nanoseconds>(finish - start).count()) / expRecorder.delete_num;
}
