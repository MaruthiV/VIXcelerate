# ===== VIXcelerate Makefile (root) =====

UNAME_S := $(shell uname -s)

# ---- toolchain defaults ----
ifeq ($(UNAME_S),Darwin)                   # macOS
  CXX       ?= clang++
  LIBOMP    := $(shell brew --prefix libomp 2>/dev/null)
  ifeq ($(LIBOMP),)
    $(error libomp not found. Install with: brew install libomp)
  endif
  OMP_CXXFLAGS := -Xpreprocessor -fopenmp -I$(LIBOMP)/include
  OMP_LDFLAGS  := -L$(LIBOMP)/lib -Wl,-rpath,$(LIBOMP)/lib -lomp
else                                        # Linux (assumes GCC)
  CXX       ?= g++
  OMP_CXXFLAGS := -fopenmp
  OMP_LDFLAGS  :=
endif

# ---- common flags ----
CXXFLAGS  ?= -std=c++17 -O3 -DNDEBUG -Wall -Wextra -Iinclude

# ---- sources / outputs ----
SRCS      := vix/main.cpp vix/runfunc.cpp
OUTDIR    := vix
SEQ_BIN   := $(OUTDIR)/vix_seq
OMP_BIN   := $(OUTDIR)/vix_omp

# ---- phony targets ----
.PHONY: all clean bench help

all: $(SEQ_BIN) $(OMP_BIN)

$(SEQ_BIN): $(SRCS)
	$(CXX) $(CXXFLAGS) $(SRCS) -o $@

$(OMP_BIN): $(SRCS)
	$(CXX) $(CXXFLAGS) $(OMP_CXXFLAGS) $(SRCS) $(OMP_LDFLAGS) -o $@

# Quick benchmark (strong scaling) — generates plots/*.png
bench: $(SEQ_BIN) $(OMP_BIN)
	cd $(OUTDIR) && \
	VECLIB_MAXIMUM_THREADS=1 OMP_PROC_BIND=close OMP_PLACES=cores \
	python3 ../scripts/bench.py 48

clean:
	rm -f $(SEQ_BIN) $(OMP_BIN)

help:
	@echo "make          # build serial + OpenMP binaries"
	@echo "make vix/vix_seq   # build serial only"
	@echo "make vix/vix_omp   # build OpenMP only"
	@echo "make bench    # run quick benchmark (N=48) and produce plots"
	@echo "make clean    # remove binaries"
