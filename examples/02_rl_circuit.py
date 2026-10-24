"""RL 直列回路: 電圧ベクトルの「頭つなぎ」と合成。"""
from pathlib import Path

import phasorplot as pp

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"

R, XL, I = 8.0, 6.0, 10.0       # [Ω], [Ω], [A]  → V_R = 80 V, V_L = 60 V

d = pp.PhasorDiagram(mode="phasor", title="RL 直列回路")
d.add("I", I, 0, scale=5, label=r"$\dot{I}$", color="tab:green")   # 基準: 電流
d.add("V_R", R * I, 0, label=r"$\dot{V}_R$", linestyle="-")
d.add("V_L", XL * I, 90, origin="V_R", label=r"$\dot{V}_L$",
      label_offset=(-14, 0))                                         # V_R の先端から
d.add_sum("V", ["V_R", "V_L"], label=r"$\dot{V}$",
          label_offset=(12, -2))                                       # 合成
d.add_angle(None, "V", label=r"$\varphi$", radius=30)               # 実軸 → V
d.save(OUT / "rl_circuit.png")
print("saved:", OUT / "rl_circuit.png")
