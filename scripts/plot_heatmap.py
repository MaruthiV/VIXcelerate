# scripts/plot_heatmap.py
import numpy as np, matplotlib.pyplot as plt
from pathlib import Path

MAT = Path("vix") / "matcv.csv"
OUT = Path("plots") / "plots_heatmap.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

m = np.loadtxt(MAT, delimiter=",")
argmin = np.unravel_index(np.nanargmin(m), m.shape)

plt.figure()
im = plt.imshow(m, origin="lower", aspect="auto")
plt.scatter([argmin[1]],[argmin[0]], s=30)
plt.title("Objective Surface over (hc, hp)")
plt.xlabel("hp index")
plt.ylabel("hc index")
plt.colorbar(im, fraction=0.046, pad=0.04)
plt.tight_layout()
plt.savefig(OUT, dpi=180)
print(f"Saved {OUT}")
