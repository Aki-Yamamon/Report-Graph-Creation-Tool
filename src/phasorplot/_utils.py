"""内部ユーティリティ(複素数変換・軸範囲の丸め・日本語フォント検出)。"""

from __future__ import annotations

import cmath
import math
from typing import Optional

from matplotlib import font_manager

# 自動検出の優先順位(上にあるものほど優先)
JAPANESE_FONT_CANDIDATES = (
    "Yu Gothic",
    "YuGothic",
    "Meiryo",
    "Hiragino Sans",
    "Hiragino Maru Gothic Pro",
    "IPAexGothic",
    "IPAGothic",
    "IPAPGothic",
    "TakaoPGothic",
    "Noto Sans CJK JP",
    "Noto Sans JP",
    "Noto Serif CJK JP",
    "MS Gothic",
)


def to_complex(magnitude: float, angle: float, unit: str = "deg") -> complex:
    """大きさと角度から複素数を作る。"""
    theta = math.radians(angle) if unit == "deg" else float(angle)
    return cmath.rect(magnitude, theta)


def nice_ceil(x: float) -> float:
    """x 以上で「キリのいい数」(1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10 × 10^n)に切り上げる。"""
    if x <= 0:
        return 1.0
    base = 10.0 ** math.floor(math.log10(x))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * base >= x * (1 - 1e-9):
            return round(m * base, 12)
    return 10.0 * base


def find_japanese_font() -> Optional[str]:
    """インストール済みの日本語フォント名を 1 つ返す。無ければ None。"""
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in JAPANESE_FONT_CANDIDATES:
        if name in available:
            return name
    return None
