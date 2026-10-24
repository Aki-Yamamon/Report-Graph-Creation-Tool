"""最小の使用例: 電圧と電流のフェーザ図 / 極座標図。"""
from pathlib import Path

import phasorplot as pp

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"

# --- 1 行で作る ---------------------------------------------------------
pp.plot({"V": (100, 0), "I": (5, -30)}, mode="phasor", save=OUT / "basic_phasor.png")

# --- 極座標に切り替えるのは mode を変えるだけ ----------------------------
pp.plot({"V": (100, 0), "I": (5, -30)}, mode="polar", save=OUT / "basic_polar.png")

# --- 角度やラベルを足す --------------------------------------------------
d = pp.PhasorDiagram(mode="phasor", title="電圧と電流の位相関係", show_values=True)
d.add("V", 100, 0, label=r"$\dot{V}$")
d.add("I", 5, -30, scale=15, label=r"$\dot{I}$")      # 電流は 15 倍して表示
d.add_angle("V", "I", label=r"$\varphi$")             # 角度を円弧と値で表示
d.save(OUT / "basic_angle.png")
print("saved:", OUT)
