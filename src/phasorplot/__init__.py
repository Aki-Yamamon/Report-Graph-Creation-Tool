"""phasorplot - レポート用のフェーザ図 / 極座標図を簡単に作るライブラリ。

最小の使い方::

    import phasorplot as pp

    pp.plot({"V": (100, 0), "I": (5, -30)}, mode="phasor", save="out.png")

細かく制御したいとき::

    d = pp.PhasorDiagram(mode="polar", title="RL 回路")
    d.add("V", 100, 0).add("I", 5, -30, scale=20)
    d.add_angle("V", "I", label=r"$\\varphi$")
    d.save("out.png")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from .diagram import PhasorDiagram

__all__ = ["PhasorDiagram", "plot", "__version__"]
__version__ = "0.1.0"


def plot(
    phasors: Dict[str, Any],
    *,
    mode: str = "phasor",
    save: Optional[Union[str, Path]] = None,
    show: bool = False,
    dpi: int = 300,
    **diagram_options: Any,
) -> PhasorDiagram:
    """辞書からワンショットでフェーザ図を作る。

    Parameters
    ----------
    phasors : dict
        ``{名前: 値}`` の辞書。値は次のいずれか。

        * ``(大きさ, 角度)``
        * ``(大きさ, 角度, {オプション})``  … :meth:`PhasorDiagram.add` のオプション
        * 複素数 ``3 + 4j``
    mode : {"phasor", "polar"}
        図の種類。
    save : str | Path, optional
        指定するとその場で画像を保存する。
    show : bool
        True なら画面にも表示する。
    dpi : int
        保存時の解像度。
    **diagram_options
        :class:`PhasorDiagram` のコンストラクタ引数(``title`` や ``angle_unit`` など)。

    Returns
    -------
    PhasorDiagram
        返ってきた図に ``add_angle`` などを足して ``save`` し直すこともできる。
    """
    diagram = PhasorDiagram(mode=mode, **diagram_options)
    for name, spec in phasors.items():
        if isinstance(spec, complex):
            diagram.add_complex(name, spec)
        elif isinstance(spec, (tuple, list)) and len(spec) == 2:
            diagram.add(name, spec[0], spec[1])
        elif isinstance(spec, (tuple, list)) and len(spec) == 3:
            diagram.add(name, spec[0], spec[1], **spec[2])
        else:
            raise ValueError(
                f"{name!r}: 値は (大きさ, 角度) / (大きさ, 角度, {{オプション}}) / 複素数 のいずれかにしてください"
            )
    if save is not None:
        diagram.save(save, dpi=dpi)
    if show:
        diagram.show()
    return diagram
