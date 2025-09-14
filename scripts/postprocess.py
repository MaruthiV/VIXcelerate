import argparse, csv, math
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def load(csv_path):
    rows=[]
    with open(csv_path, newline="") as f:
        r=csv.DictReader(f)
        for row in r:
            rows.append(row)
    if not rows:
        raise SystemExit(f"No rows in {csv_path}")
    # all rows share these serial fields
    ngrid      = int(rows[0]["NGRID"])
    T1_wall    = float(rows[0]["T1_wall_s"])
    T1_app     = float(rows[0]["T1_app_s"])
    hc1        = float(rows[0]["hc1"]) if rows[0]["hc1"] else float("nan")
    hp1        = float(rows[0]["hp1"]) if rows[0]["hp1"] else float("nan")
    # parallel rows
    P=[]; Tp=[]; Sp=[]; Ep=[]; Hc=[]; Hp=[]; Rss=[]
    for r in rows:
        P.append(int(r["threads"]))
        Tp.append(float(r["Tp_wall_s"]))
        Sp.append(float(r["speedup"]) if r["speedup"] else float("nan"))
        Ep.append(float(r["efficiency"]) if r["efficiency"] else float("nan"))
        Hc.append(float(r["hc_med"]) if r["hc_med"] else float("nan"))
        Hp.append(float(r["hp_med"]) if r["hp_med"] else float("nan"))
        Rss.append(float(r["maxrss_kb"]) if r["maxrss_kb"] else float("nan"))
    return ngrid, T1_wall, T1_app, hc1, hp1, np.array(P), np.array(Tp), np.array(Sp), np.array(Ep), np.array(Hc), np.array(Hp), np.array(Rss)

def amdahl_serial_fraction(P, Tp, T1):
    # fit Tp/T1 ≈ s + (1-s)/p
    p = P.astype(float)
    y = Tp.astype(float)/float(T1)
    X = np.vstack([np.ones_like(p), 1.0/p]).T
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(beta[0])

def save_speedup_serial(outdir, P, Sp, ngrid):
    plt.figure()
    plt.plot(P, Sp, marker="o", label="Measured (baseline=serial)")
    plt.plot(P, P/P[0], "--", label="Ideal")
    plt.title(f"Speedup vs Serial Baseline (N={ngrid})")
    plt.xlabel("Threads")
    plt.ylabel("Speedup (T_serial / T_p)")
    plt.legend(); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"speedup_vs_serial.png", dpi=180)

def save_speedup_parallel(outdir, P, Tp, ngrid):
    # normalize to parallel p=1 time so Speedup(1)=1
    if 1 not in set(P.tolist()):
        return
    T1p = Tp[P.tolist().index(1)]
    Sp_par = T1p / Tp
    plt.figure()
    plt.plot(P, Sp_par, marker="o", label="Measured (baseline=parallel p=1)")
    plt.plot(P, P/P[0], "--", label="Ideal")
    plt.title(f"Speedup vs Parallel p=1 (N={ngrid})")
    plt.xlabel("Threads")
    plt.ylabel("Speedup (T_p=1 / T_p)")
    plt.legend(); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"speedup_parallel_baseline.png", dpi=180)

def save_correctness_table(outdir, P, Hc, Hp, hc1, hp1):
    lines = []
    lines.append("| Threads | hc (median) | Δhc | hp (median) | Δhp |")
    lines.append("|--------:|------------:|----:|------------:|----:|")
    for p, hc, hp in zip(P, Hc, Hp):
        dhc = hc - hc1 if not (math.isnan(hc) or math.isnan(hc1)) else float("nan")
        dhp = hp - hp1 if not (math.isnan(hp) or math.isnan(hp1)) else float("nan")
        lines.append(f"| {p} | {hc:.4f} | {dhc:+.4f} | {hp:.4f} | {dhp:+.4f} |")
    content = [
        "### Correctness (serial vs parallel medians)\n",
        f"Serial baseline: **hc = {hc1:.4f}**, **hp = {hp1:.4f}**.\n",
        "Values below are medians over repeats for each thread count.\n",
        "\n",
        *[l+"\n" for l in lines]
    ]
    (outdir/"correctness_table.md").write_text("".join(content))

def save_summary(outdir, P, Tp, T1_wall, Ep):
    best_i = int(np.argmin(Tp))
    best_p = int(P[best_i]); best_Tp = float(Tp[best_i])
    Sp = T1_wall / best_Tp
    Eff = float(Ep[best_i]) if best_i < len(Ep) else (Sp/best_p)
    txt = (f"Serial T1 (wall): {T1_wall:.3f} s\n"
           f"Best parallel: p={best_p}, T_p={best_Tp:.3f} s\n"
           f"Speedup T1/Tp: {Sp:.2f}x  |  Efficiency: {Eff:.2f}\n")
    (outdir/"summary.txt").write_text(txt)

def save_throughput(outdir, P, Tp, ngrid, nstrike, mrange):
    # QP count = nstrike * ngrid^2 * (mrange + 1)
    QP = nstrike * (ngrid**2) * (mrange + 1)
    thr = QP / Tp  # QP per second
    plt.figure()
    plt.plot(P, thr/1e6, marker="o")
    plt.title(f"Throughput vs Threads (N={ngrid}, strikes={nstrike}, mRange={mrange})")
    plt.xlabel("Threads"); plt.ylabel("Throughput (million QP/s)")
    plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"throughput.png", dpi=180)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="plots/bench_results.csv")
    ap.add_argument("--mrange", type=int, default=None, help="x-grid size used internally (mRange)")
    ap.add_argument("--nstrike", type=int, default=None, help="# of unique strikes (often 30)")
    args = ap.parse_args()

    outdir = Path("plots"); outdir.mkdir(exist_ok=True, parents=True)
    ngrid, T1_wall, T1_app, hc1, hp1, P, Tp, Sp, Ep, Hc, Hp, Rss = load(args.csv)

    # Alternate speedup views
    save_speedup_serial(outdir, P, Sp, ngrid)
    save_speedup_parallel(outdir, P, Tp, ngrid)

    # Correctness table + summary
    save_correctness_table(outdir, P, Hc, Hp, hc1, hp1)
    save_summary(outdir, P, Tp, T1_wall, Ep)

    # Amdahl estimate
    try:
        s = amdahl_serial_fraction(P, Tp, T1_wall)
        (outdir/"amdahl.txt").write_text(f"Estimated serial fraction s ≈ {s:.4f}\n")
    except Exception:
        pass

    # Optional throughput
    if args.mrange is not None and args.nstrike is not None:
        save_throughput(outdir, P, Tp, ngrid, args.nstrike, args.mrange)

    print("Wrote: speedup_vs_serial.png, speedup_parallel_baseline.png, correctness_table.md, summary.txt",
          "+ throughput.png (if mrange/nstrike provided)")

if __name__ == "__main__":
    main()
