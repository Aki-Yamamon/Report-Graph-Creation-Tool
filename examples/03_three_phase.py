"""三相交流: 相電圧と線間電圧。"""
from pathlib import Path

import phasorplot as pp

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"

d = pp.PhasorDiagram(mode="phasor", title="三相電圧", show_values=True)
d.add("Va", 100, 0)
d.add("Vb", 100, -120)
d.add("Vc", 100, 120)
d.add_difference("Vab", "Va", "Vb", linestyle="--", label=r"$V_{ab}$",
                 label_offset=(0, 20))                                  # 線間電圧
d.save(OUT / "three_phase.png")

# 同じデータを極座標でも
d.mode = "polar"
d.save(OUT / "three_phase_polar.png")
print("saved:", OUT)
