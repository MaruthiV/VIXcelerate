# scripts/bench.py
import os, sys, subprocess, time, re, csv, statistics as stats, shutil, platform
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# ---------- config ----------
BIN_DIR   = Path("vix")
SEQ_BIN   = BIN_DIR / "vix_seq"
OMP_BIN   = BIN_DIR / "vix_omp"
OUT_DIR   = Path("plots")
THREADS   = [1, 2, 4, 6, 8]
REPEATS   = 3
NGRID     = int(sys.argv[1]) if len(sys.argv) > 1 else 48

APP_TIME_RE = re.compile(r"\[bandwidth_grid_total\]\s+([\d\.]+)\s*s")
HC_RE       = re.compile(r"hc:\s*([0-9.]+)")
HP_RE       = re.compile(r"hp:\s*([0-9.]+)")

IS_MAC = (platform.system() == "Darwin")
TIME_BIN = shutil.which("/usr/bin/time") or shutil.which("time")

def ensure_paths():
    if not SEQ_BIN.exists() or not OMP_BIN.exists():
        sys.exit(f"ERROR: build the binaries first: `make` (looking for {SEQ_BIN} and {OMP_BIN})")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def run_one(cmd, threads=None):
    env = os.environ.copy()
    # keep background libs from stealing threads
    env["VECLIB_MAXIMUM_THREADS"] = "1"
    env["OMP_PROC_BIND"] = "close"
    env["OMP_PLACES"] = "cores"
    if threads is not None:
        env["OMP_NUM_THREADS"] = str(threads)

    # Use /usr/bin/time to get Max RSS when possible
    full_cmd = cmd
    if TIME_BIN:
        if IS_MAC:
            full_cmd = [TIME_BIN, "-l"] + cmd
        else:
            full_cmd = [TIME_BIN, "-v"] + cmd

    t0 = time.perf_counter()
    p = subprocess.run(full_cmd, cwd=BIN_DIR, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    t1 = time.perf_counter()

    out = p.stdout
    err = p.stderr
    wall = t1 - t0

    # parse internal app timer (if present)
    m = APP_TIME_RE.search(out) or APP_TIME_RE.search(err)
    app_time = float(m.group(1)) if m else float("nan")

    # parse hc/hp
    hc = float(HC_RE.search(out).group(1)) if HC_RE.search(out) else float("nan")
    hp = float(HP_RE.search(out).group(1)) if HP_RE.search(out) else float("nan")

    # parse Max RSS
    maxrss_kb = float("nan")
    s = f"{out}\n{err}".lower()
    for key in ["maximum resident set size", "maximum resident set size (kbytes)"]:
        if key in s:
            # try to pull the last integer on that line
            for line in (f"{out}\n{err}").splitlines():
                if key in line.lower():
                    toks = re.findall(r"(\d+)", line)
                    if toks:
                        maxrss_kb = float(toks[-1])
                    break
            break

    return {"wall_s": wall, "app_s": app_time, "maxrss_kb": maxrss_kb, "hc": hc, "hp": hp, "rc": p.returncode, "out": out, "err": err}

def med(vals): return stats.median(vals) if vals else float("nan")

def amdahl_serial_fraction(p_list, Tp_list, T1):
    # fit Tp/T1 ≈ s + (1-s)/p
    p = np.array(p_list, dtype=float)
    y = np.array(Tp_list, dtype=float) / float(T1)
    X = np.vstack([np.ones_like(p), 1.0/p]).T
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    s = float(beta[0])  # serial fraction
    return s

def main():
    ensure_paths()

    # Serial baseline
    serial_runs = [run_one([str(SEQ_BIN), str(NGRID)], threads=1) for _ in range(REPEATS)]
    T1_wall = med([r["wall_s"] for r in serial_runs])
    T1_app  = med([r["app_s"]  for r in serial_runs])
    hc1     = med([r["hc"] for r in serial_runs])
    hp1     = med([r["hp"] for r in serial_runs])

    # Parallel runs
    rows = []
    for pthr in THREADS:
        runs = [run_one([str(OMP_BIN), str(NGRID)], threads=pthr) for _ in range(REPEATS)]
        Tp_wall = med([r["wall_s"] for r in runs])
        Tp_app  = med([r["app_s"]  for r in runs])
        rss_kb  = med([r["maxrss_kb"] for r in runs if not np.isnan(r["maxrss_kb"])])
        hc_med  = med([r["hc"] for r in runs])
        hp_med  = med([r["hp"] for r in runs])

        Sp = T1_wall / Tp_wall if Tp_wall > 0 else float("nan")
        Ep = Sp / pthr if pthr > 0 else float("nan")

        rows.append({
            "threads": pthr,
            "Tp_wall_s": Tp_wall,
            "Tp_app_s": Tp_app,
            "speedup": Sp,
            "efficiency": Ep,
            "maxrss_kb": rss_kb,
            "hc_med": hc_med,
            "hp_med": hp_med
        })

    # write CSV
    csv_path = OUT_DIR / "bench_results.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["NGRID","T1_wall_s","T1_app_s","hc1","hp1","threads","Tp_wall_s","Tp_app_s","speedup","efficiency","maxrss_kb","hc_med","hp_med"])
        w.writeheader()
        for r in rows:
            r2 = {"NGRID": NGRID, "T1_wall_s": T1_wall, "T1_app_s": T1_app, "hc1": hc1, "hp1": hp1}
            r2.update(r)
            w.writerow(r2)

    # plots
    p  = np.array([r["threads"] for r in rows], dtype=float)
    Tp = np.array([r["Tp_wall_s"] for r in rows], dtype=float)
    Sp = np.array([r["speedup"]   for r in rows], dtype=float)
    Ep = np.array([r["efficiency"]for r in rows], dtype=float)
    R  = np.array([r["maxrss_kb"] for r in rows], dtype=float)

    plt.figure()
    plt.plot(p, Tp, marker="o")
    plt.title(f"Strong Scaling (N={NGRID}) — Wall Time")
    plt.xlabel("Threads")
    plt.ylabel("Time (s)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "time_vs_threads.png", dpi=180)

    plt.figure()
    plt.plot(p, Sp, marker="o", label="Measured")
    plt.plot(p, p/p[0], "--", label="Ideal")
    plt.title(f"Speedup (T1/Tp) (N={NGRID})")
    plt.xlabel("Threads")
    plt.ylabel("Speedup")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "speedup.png", dpi=180)

    plt.figure()
    plt.plot(p, Ep, marker="o")
    plt.title(f"Efficiency (Speedup / p) (N={NGRID})")
    plt.xlabel("Threads")
    plt.ylabel("Efficiency")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "efficiency.png", dpi=180)

    # Memory plot if we have RSS
    if not np.all(np.isnan(R)):
        plt.figure()
        plt.plot(p, R/1024.0, marker="o")  # MB
        plt.title(f"Memory vs Threads (N={NGRID}) — Max RSS")
        plt.xlabel("Threads")
        plt.ylabel("Max RSS (MB)")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "memory_vs_threads.png", dpi=180)

    # Amdahl serial fraction
    try:
        s = amdahl_serial_fraction(p, Tp, T1_wall)
        with open(OUT_DIR / "amdahl.txt", "w") as f:
            f.write(f"Estimated serial fraction s ≈ {s:.4f}\n")
    except Exception:
        pass

    print(f"Wrote {csv_path}")
    print("Saved plots: time_vs_threads.png, speedup.png, efficiency.png",
          "(+ memory_vs_threads.png) in ./plots")

if __name__ == "__main__":
    main()
