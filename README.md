# VIXcelerate — CPU-parallel bandwidth search for option RND

VIXcelerate calibrates a VIX-style **nonparametric risk-neutral density (RND)** and accelerates the bottleneck—evaluating a 2D bandwidth grid \((h_c,h_p)\) with millions of tiny QP solves—using **OpenMP** on CPU. It outputs the optimal \((h_c,h_p)\) and judge-ready scaling plots (time, speedup, efficiency). Option data files are included for an out-of-the-box run.

## Why this matters
RND calibration is compute-heavy and traditionally slow. Parallelizing the \((h_c,h_p)\) grid on a laptop makes frequent (even intraday) refresh feasible without a cluster.

## Project Structure

```
├── include/           # Header files
│   ├── ls.hpp        # Linear solver utilities
│   ├── nprnd.hpp     # Nonparametric RND core implementation
│   ├── qp.hpp        # Quadratic programming solver
│   └── runfunc.hpp   # Runtime function declarations
├── vix/              # VIX dataset implementation
│   ├── main.cpp      # Main execution file
│   ├── runfunc.cpp   # Runtime functions and data loading
│   ├── callprice.txt # Call option prices
│   ├── callstrike.txt# Call option strikes
│   ├── callopenint.txt# Call option open interest (weights)
│   ├── putprice.txt  # Put option prices
│   ├── putstrike.txt # Put option strikes
│   ├── putopenint.txt# Put option open interest (weights)
│   ├── strike.txt    # Unique strike prices
│   ├── vix           # Sequential executable
│   ├── vix_omp       # OpenMP parallel executable
│   └── vix_seq       # Sequential reference executable
├── plots/            # Performance plots and results
├── scripts/          # Analysis and plotting scripts
└── README.md         # This file
```

## Algorithm Overview

The implementation uses a **nonparametric approach** to estimate risk-neutral densities from option prices:

1. **Data Input**: Load call/put option prices, strikes, and open interest weights
2. **Grid Search**: Evaluate bandwidth pairs \((h_c, h_p)\) over a 2D grid
3. **Cross-Validation**: For each \((h_c, h_p)\) pair, perform leave-one-out cross-validation
4. **QP Optimization**: Solve quadratic programming problems to fit local polynomial estimators
5. **Parallel Execution**: Use OpenMP to parallelize the bandwidth grid evaluation
6. **Optimal Selection**: Find the \((h_c, h_p)\) pair that minimizes the cross-validation criterion

### Key Features

- **OpenMP Parallelization**: The bandwidth grid search is parallelized using `#pragma omp parallel for collapse(2)`
- **Efficient QP Solver**: Custom quadratic programming implementation for fast local polynomial fitting
- **Cross-Validation**: Leave-one-out cross-validation with area, entropy, and variation penalties
- **Memory Efficient**: Optimized memory management for large-scale computations

## Quick Start

### Prerequisites

- C++11 compatible compiler (clang++, g++)
- OpenMP support
- Standard math libraries

### Compilation

```bash
cd vix/
clang++ -std=c++11 -O2 -fopenmp -I"../include" runfunc.cpp main.cpp -o vix_omp
```

### Running the Code

```bash
# Run with a 256x256 bandwidth grid
./vix_omp 256
```

### Default Parameters

- **Bandwidth Grid**: \(h_c, h_p \in [0.75, 2.0]\) with configurable resolution
- **Underlying Grid**: \([10.0, 47.5]\) with 128 points
- **Risk-free Rate**: \(r = 0.02\)
- **Time to Maturity**: \(\tau = 1/12\) (1 month)

## Performance Characteristics

The parallel implementation provides significant speedup over sequential execution:

- **Grid Size**: Configurable (e.g., 256×256 = 65,536 bandwidth pairs)
- **QP Problems**: Millions of small quadratic programming problems
- **Parallel Efficiency**: Near-linear speedup on multi-core CPUs
- **Memory Usage**: Optimized for large-scale computations

### Expected Runtime

- **Sequential**: Several hours for large grids
- **Parallel (8 cores)**: ~10-30 minutes for 256×256 grid
- **Scaling**: Near-linear speedup with core count

## Output

The program outputs:

1. **Optimal Bandwidths**: Best \((h_c, h_p)\) pair
2. **Performance Metrics**: 
   - Number of QP problems solved
   - Total iterations
   - Execution time
3. **Cross-Validation Results**: Area, entropy, and variation statistics

Example output:
```
Number of calls:   150
Number of puts:    120
Number of strikes: 45
hc: 1.2345
hp: 1.6789
number of solved QP problems: 2949120
number of iterations: 58982400
The elapsed time is 1245.67 seconds
```

## Customization

### Modifying Parameters

Edit `main.cpp` to change:
- Bandwidth grid ranges: `(0.75, 2.0)` for both \(h_c\) and \(h_p\)
- Underlying grid: `(10.0, 47.5)` with 128 points
- Risk-free rate and time to maturity

### Using Different Data

Replace the data files in `vix/` directory:
- `callprice.txt`, `callstrike.txt`, `callopenint.txt`
- `putprice.txt`, `putstrike.txt`, `putopenint.txt`
- `strike.txt`

Maintain the same file format (one value per line).

## Technical Details

### Parallel Implementation

The core parallelization occurs in the `mat_cv` function:

```cpp
#pragma omp parallel for collapse(2) schedule(dynamic,8)
for (int i = 0; i < nhc; ++i) {
    for (int j = 0; j < nhp; ++j) {
        // Cross-validation computation for (h_c[i], h_p[j])
    }
}
```

### Cross-Validation Criterion

The optimization minimizes:
\[
CV(h_c, h_p) = \sum_{k} \left[ CV_k \cdot V_k + \frac{1 + |A_k - 1|}{E_k} \right]
\]

Where:
- \(CV_k\): Cross-validation error for strike \(k\)
- \(V_k\): Variation penalty
- \(A_k\): Area constraint
- \(E_k\): Entropy measure

## Research Applications

This implementation is designed for:
- **Risk Management**: Real-time RND estimation for portfolio risk assessment
- **Option Pricing**: Nonparametric option pricing models
- **Market Analysis**: Volatility surface construction and analysis
- **Academic Research**: Benchmarking and methodology development

## Future Enhancements

- GPU acceleration using CUDA
- Additional datasets (S&P500, etc.)
- Advanced parallelization strategies
- Real-time data integration
- Web-based visualization interface

## License

MIT License

Copyright (c) 2024 VIXcelerate

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

