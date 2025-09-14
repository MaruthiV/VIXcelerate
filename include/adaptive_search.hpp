#ifndef ADAPTIVE_SEARCH_HPP
#define ADAPTIVE_SEARCH_HPP

#include "nprnd.hpp"
#include <vector>
#include <algorithm>

class AdaptiveBandwidthOptimizer {
private:
    NPRND* rnd_estimator;
    
    struct GridPoint {
        double hc, hp, objective;
        bool evaluated;
    };
    
public:
    AdaptiveBandwidthOptimizer(NPRND* estimator) : rnd_estimator(estimator) {}
    
    void adaptive_search(double* hoptim, double hc_min, double hc_max, 
                        double hp_min, double hp_max, int initial_grid = 32) {
        
        // Start with coarse grid evaluation
        std::vector<double> hc_coarse = linspace(hc_min, hc_max, initial_grid);
        std::vector<double> hp_coarse = linspace(hp_min, hp_max, initial_grid);
        
        // Find best coarse solution
        double best_obj = 1e10;
        int best_i = 0, best_j = 0;
        
        double* coarse_results = (double*)calloc(initial_grid * initial_grid, sizeof(double));
        rnd_estimator->mat_cv_optimized(coarse_results, hc_coarse.data(), initial_grid, 
                                       hp_coarse.data(), initial_grid);
        
        for (int i = 0; i < initial_grid; i++) {
            for (int j = 0; j < initial_grid; j++) {
                if (coarse_results[i * initial_grid + j] < best_obj) {
                    best_obj = coarse_results[i * initial_grid + j];
                    best_i = i; best_j = j;
                }
            }
        }
        
        // Refine around best point
        double hc_center = hc_coarse[best_i];
        double hp_center = hp_coarse[best_j];
        double hc_width = (hc_max - hc_min) / initial_grid;
        double hp_width = (hp_max - hp_min) / initial_grid;
        
        // Fine grid around best point
        std::vector<double> hc_fine = linspace(hc_center - hc_width, hc_center + hc_width, initial_grid);
        std::vector<double> hp_fine = linspace(hp_center - hp_width, hp_center + hp_width, initial_grid);
        
        double* fine_results = (double*)calloc(initial_grid * initial_grid, sizeof(double));
        rnd_estimator->mat_cv_optimized(fine_results, hc_fine.data(), initial_grid, 
                                       hp_fine.data(), initial_grid);
        
        // Find refined optimum
        best_obj = 1e10;
        for (int i = 0; i < initial_grid; i++) {
            for (int j = 0; j < initial_grid; j++) {
                if (fine_results[i * initial_grid + j] < best_obj) {
                    best_obj = fine_results[i * initial_grid + j];
                    hoptim[0] = hc_fine[i];
                    hoptim[1] = hp_fine[j];
                }
            }
        }
        
        free(coarse_results);
        free(fine_results);
    }
    
private:
    std::vector<double> linspace(double start, double end, int num) {
        std::vector<double> result(num);
        double step = (end - start) / (num - 1);
        for (int i = 0; i < num; i++) {
            result[i] = start + i * step;
        }
        return result;
    }
};

#endif