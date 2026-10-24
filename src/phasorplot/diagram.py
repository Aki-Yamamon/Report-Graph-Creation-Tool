"""フェーザ図 / 極座標図を、メソッドを呼ぶだけで作れる PhasorDiagram クラス。"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rc_context
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from ._utils import find_japanese_font, nice_ceil, to_complex

# 位置の指定方法: フェーザ名(その先端) / 複素数 / (x, y) タプル
PointLike = Union[str, complex, float, int, Tuple[float, float]]

_MODE_ALIASES = {
    "phasor": "phasor",
    "complex": "phasor",
    "cartesian": "phasor",
    "フェーザ": "phasor",
    "polar": "polar",
    "極座標": "polar",
    "極座": "polar",
}

_DEFAULT_COLORS = (
    "#1f77b4",  # blue
    "#d62728",  # red
    "#2ca02c",  # green
    "#ff7f0e",  # orange
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#17becf",  # cyan
)

_ARC_LABEL_BBOX = dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75)


# --------------------------------------------------------------------------- #
# 内部データ構造
# --------------------------------------------------------------------------- #
@dataclass
class _Phasor:
    name: str
    z: complex  # 実際の値
    scale: float  # 表示倍率(図上では z * scale の長さで描く)
    origin: complex  # 描画の始点(図上の座標)
    color: str
    linestyle: str
    linewidth: float
    alpha: float
    label: str
    show_value: bool
    components: bool
    label_offset: Tuple[float, float]

    @property
    def vec(self) -> complex:
        """図上で描かれるベクトル。"""
        return self.z * self.scale

    @property
    def tip(self) -> complex:
        """図上での矢印の先端。"""
        return self.origin + self.vec


@dataclass
class _Arc:
    center: complex
    start_angle: float  # [rad]
    delta: float  # [rad] (符号付き)
    radius: float
    text: str
    color: str
    linestyle: str
    linewidth: float
    fontsize: Optional[float]
    label_pos: complex


@dataclass
class _Line:
    start: complex
    end: complex
    color: str
    linestyle: str
    linewidth: float
    alpha: float


@dataclass
class _Text:
    pos: complex
    text: str
    color: str
    fontsize: Optional[float]
    ha: str
    va: str


# --------------------------------------------------------------------------- #
# 本体
# --------------------------------------------------------------------------- #
class PhasorDiagram:
    """フェーザ図 / 極座標図を作るクラス。

    Parameters
    ----------
    mode : {"phasor", "polar"}
        ``"phasor"`` : 複素平面(実軸・虚軸)に矢印を描くフェーザ図。
        ``"polar"``  : 極座標(円形グリッド)に矢印を描く図。
        日本語の ``"フェーザ"`` / ``"極座標"`` も使えます。
    angle_unit : {"deg", "rad"}
        角度の入力・表示単位。既定は度。
    title : str, optional
        図のタイトル。
    figsize : (float, float)
        画像サイズ[inch]。
    grid : bool
        グリッドを表示するか。
    show_values : bool
        True にすると、全フェーザのラベルに ``100∠30°`` のような値を付ける。
        個別には ``add(..., show_value=True/False)`` で上書きできる。
    legend : bool
        凡例を表示するか。
    limit : float, optional
        軸の範囲を固定する。phasor では ±limit、polar では 0〜limit。
        省略時は自動。
    angle_step : float
        polar モードの角度目盛の間隔[deg]。
    font : str, optional
        使用するフォント名。省略時は日本語フォントを自動検出する。
    font_size : float
        ラベルの文字サイズ。
    xlabel, ylabel : str
        phasor モードの軸ラベル。
    """

    def __init__(
        self,
        mode: str = "phasor",
        *,
        angle_unit: str = "deg",
        title: Optional[str] = None,
        figsize: Tuple[float, float] = (6.0, 6.0),
        grid: bool = True,
        show_values: bool = False,
        legend: bool = False,
        limit: Optional[float] = None,
        angle_step: float = 30.0,
        font: Optional[str] = None,
        font_size: float = 12.0,
        xlabel: str = "Re",
        ylabel: str = "Im",
    ) -> None:
        key = str(mode).strip().lower()
        if key not in _MODE_ALIASES:
            raise ValueError(
                f"mode は 'phasor' か 'polar' を指定してください(指定値: {mode!r})"
            )
        if angle_unit not in ("deg", "rad"):
            raise ValueError("angle_unit は 'deg' か 'rad' を指定してください")

        self.mode: str = _MODE_ALIASES[key]
        self.angle_unit = angle_unit
        self.title = title
        self.figsize = figsize
        self.grid = grid
        self.show_values = show_values
        self.legend = legend
        self.limit = limit
        self.angle_step = angle_step
        self.font = font
        self.font_size = font_size
        self.xlabel = xlabel
        self.ylabel = ylabel

        self._phasors: Dict[str, _Phasor] = {}
        self._auto_color_count = 0
        self._arcs: List[_Arc] = []
        self._lines: List[_Line] = []
        self._texts: List[_Text] = []

    # ------------------------------------------------------------------ #
    # 要素の追加
    # ------------------------------------------------------------------ #
    def add(
        self,
        name: str,
        magnitude: float,
        angle: float = 0.0,
        *,
        origin: Optional[PointLike] = None,
        scale: float = 1.0,
        color: Optional[str] = None,
        linestyle: str = "-",
        linewidth: float = 2.0,
        alpha: float = 1.0,
        label: Optional[str] = None,
        show_value: Optional[bool] = None,
        components: bool = False,
        label_offset: Tuple[float, float] = (0.0, 0.0),
    ) -> "PhasorDiagram":
        """大きさと角度でフェーザを追加する。

        Parameters
        ----------
        name : str
            フェーザの名前(他のメソッドから参照するキー。重複不可)。
        magnitude : float
            大きさ(実効値や振幅など)。
        angle : float
            位相角。単位は ``angle_unit`` に従う。
        origin : str | complex | (x, y), optional
            矢印の始点。省略すると原点。フェーザ名を渡すとその先端から描く
            (ベクトルの「頭つなぎ」ができる)。
        scale : float
            表示倍率。電圧と電流のように桁が違うときに ``scale=20`` などとする。
            ラベルには ``(×20)`` が自動で付く。
        color, linestyle, linewidth, alpha :
            matplotlib と同じ見た目の指定。
        label : str, optional
            図に表示する文字列。省略すると ``name``。``r"$\\dot{V}_1$"`` のような
            数式も使える。
        show_value : bool, optional
            ラベルに ``大きさ∠角度`` を付けるか。省略時はコンストラクタの設定。
        components : bool
            True にすると実部・虚部への射影(点線)を描く。
        label_offset : (dx, dy)
            ラベルの位置を右・上方向に [pt] 単位でずらす。ラベル同士が重なったとき用。
        """
        z = to_complex(magnitude, angle, self.angle_unit)
        return self._add_z(
            name,
            z,
            origin=origin,
            scale=scale,
            color=color,
            linestyle=linestyle,
            linewidth=linewidth,
            alpha=alpha,
            label=label,
            show_value=show_value,
            components=components,
            label_offset=label_offset,
        )

    def add_complex(self, name: str, z: complex, **options) -> "PhasorDiagram":
        """複素数 ``z`` でフェーザを追加する。``options`` は :meth:`add` と同じ。"""
        return self._add_z(name, complex(z), **options)

    def add_sum(
        self, name: str, names: Sequence[str], **options
    ) -> "PhasorDiagram":
        """既存フェーザの合成(ベクトル和)を追加する。

        例: ``d.add_sum("V", ["V_R", "V_L"])``。
        合成するフェーザの ``scale`` は同じである必要がある。
        既定では黒色で原点から描く。
        """
        if not names:
            raise ValueError("names に 1 つ以上のフェーザ名を指定してください")
        members = [self._get(n) for n in names]
        scales = {m.scale for m in members}
        if len(scales) != 1:
            raise ValueError("scale が異なるフェーザは合成できません")
        options.setdefault("scale", members[0].scale)
        options.setdefault("color", "black")
        return self._add_z(name, sum(m.z for m in members), **options)

    def add_difference(
        self, name: str, minuend: str, subtrahend: str, **options
    ) -> "PhasorDiagram":
        """差 ``minuend - subtrahend`` のフェーザを追加する(線間電圧など)。

        既定では ``subtrahend`` の先端から ``minuend`` の先端へ向かう矢印になる。
        (2 つのフェーザの始点が同じ場合に幾何学的に正しい位置)
        """
        a, b = self._get(minuend), self._get(subtrahend)
        if a.scale != b.scale:
            raise ValueError("scale が異なるフェーザの差は取れません")
        options.setdefault("scale", a.scale)
        options.setdefault("origin", subtrahend)
        options.setdefault("color", "black")
        return self._add_z(name, a.z - b.z, **options)

    def add_angle(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        *,
        label: Optional[str] = None,
        radius: Optional[float] = None,
        center: Optional[PointLike] = None,
        color: str = "0.25",
        linestyle: str = "-",
        linewidth: float = 1.2,
        show_value: bool = True,
        signed: bool = False,
        precision: Optional[int] = None,
        fontsize: Optional[float] = None,
        label_distance: float = 1.45,
    ) -> "PhasorDiagram":
        """2 つのフェーザ間の角度を円弧と文字で描く。

        ``start`` / ``end`` にフェーザ名を渡す。``None`` は実軸(0°)を意味する。

        例
        --
        ``d.add_angle("V", "I", label=r"$\\varphi$")``   → V と I の間の角度
        ``d.add_angle(None, "V", label=r"$\\theta$")``    → 実軸から V までの角度

        Parameters
        ----------
        label : str, optional
            角度の記号。``show_value=True`` なら ``φ = 30°`` のように値が続く。
            省略すると値だけ(``30°``)を表示する。
        radius : float, optional
            円弧の半径(図上の長さ)。省略時は短い方のフェーザの 30%。
            複数の円弧が重なるときに指定する。
        center : 位置, optional
            円弧の中心。省略時は ``start``(なければ ``end``)の始点。
        signed : bool
            True にすると符号付き(進み/遅れが分かる)の値を表示する。
        precision : int, optional
            小数点以下の桁数。既定は度で 1 桁、rad で 3 桁。
        label_distance : float
            文字の位置(半径に対する倍率)。
        """
        if start is None and end is None:
            raise ValueError("start と end の少なくとも一方にフェーザ名を指定してください")
        ps = self._get(start) if start is not None else None
        pe = self._get(end) if end is not None else None

        if center is not None:
            c = self._point(center)
        else:
            c = (ps or pe).origin  # type: ignore[union-attr]

        a1 = cmath.phase(ps.vec) if ps is not None else 0.0
        a2 = cmath.phase(pe.vec) if pe is not None else 0.0
        delta = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi  # 短い方の角度

        if radius is None:
            lengths = [abs(p.vec) for p in (ps, pe) if p is not None]
            radius = 0.3 * min(lengths)
        if radius <= 0:
            raise ValueError("円弧の半径が 0 以下です。radius を指定してください")

        value = delta if signed else abs(delta)
        value_text = self._format_angle(value, precision)
        if show_value:
            text = value_text if label is None else f"{label} = {value_text}"
        else:
            text = label or ""

        mid = a1 + delta / 2
        label_pos = c + radius * label_distance * cmath.exp(1j * mid)
        self._arcs.append(
            _Arc(c, a1, delta, radius, text, color, linestyle, linewidth, fontsize, label_pos)
        )
        return self

    def add_line(
        self,
        start: PointLike,
        end: PointLike,
        *,
        color: str = "0.5",
        linestyle: str = "--",
        linewidth: float = 1.0,
        alpha: float = 1.0,
    ) -> "PhasorDiagram":
        """2 点を結ぶ補助線を引く。位置にはフェーザ名(先端)も使える。

        例: 線間電圧の三角形 ``d.add_line("Va", "Vb")``
        """
        self._lines.append(
            _Line(self._point(start), self._point(end), color, linestyle, linewidth, alpha)
        )
        return self

    def add_text(
        self,
        position: PointLike,
        text: str,
        *,
        color: str = "black",
        fontsize: Optional[float] = None,
        ha: str = "center",
        va: str = "center",
    ) -> "PhasorDiagram":
        """任意の位置に文字を置く。位置にはフェーザ名(先端)も使える。"""
        self._texts.append(_Text(self._point(position), text, color, fontsize, ha, va))
        return self

    # ------------------------------------------------------------------ #
    # 出力
    # ------------------------------------------------------------------ #
    def save(
        self,
        path: Union[str, Path],
        *,
        dpi: int = 300,
        transparent: bool = False,
        bbox_inches: str = "tight",
        pad_inches: float = 0.1,
    ) -> Path:
        """画像として保存する。拡張子(.png / .pdf / .svg など)で形式が決まる。"""
        path = Path(path)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        with self._style_context():
            fig, _ = self._build(use_pyplot=False)
            fig.savefig(
                path,
                dpi=dpi,
                transparent=transparent,
                bbox_inches=bbox_inches,
                pad_inches=pad_inches,
            )
        return path

    def show(self) -> None:
        """画面に表示する(Jupyter などで確認用)。"""
        with self._style_context():
            self._build(use_pyplot=True)
            plt.show()

    def render(self) -> Tuple[Figure, "plt.Axes"]:
        """matplotlib の ``(fig, ax)`` を返す。さらに細かく手を加えたいとき用。"""
        with self._style_context():
            fig, ax = self._build(use_pyplot=False)
            FigureCanvasAgg(fig).draw()  # フォント等をこの時点で確定させる
        return fig, ax

    # ------------------------------------------------------------------ #
    # 内部: 補助
    # ------------------------------------------------------------------ #
    def _add_z(
        self,
        name: str,
        z: complex,
        *,
        origin: Optional[PointLike] = None,
        scale: float = 1.0,
        color: Optional[str] = None,
        linestyle: str = "-",
        linewidth: float = 2.0,
        alpha: float = 1.0,
        label: Optional[str] = None,
        show_value: Optional[bool] = None,
        components: bool = False,
        label_offset: Tuple[float, float] = (0.0, 0.0),
    ) -> "PhasorDiagram":
        if name in self._phasors:
            raise ValueError(f"フェーザ名 {name!r} は既に使われています")
        if color is None:
            color = _DEFAULT_COLORS[self._auto_color_count % len(_DEFAULT_COLORS)]
            self._auto_color_count += 1
        self._phasors[name] = _Phasor(
            name=name,
            z=complex(z),
            scale=float(scale),
            origin=0j if origin is None else self._point(origin),
            color=color,
            linestyle=linestyle,
            linewidth=linewidth,
            alpha=alpha,
            label=name if label is None else label,
            show_value=self.show_values if show_value is None else show_value,
            components=components,
            label_offset=label_offset,
        )
        return self

    def _get(self, name: str) -> _Phasor:
        try:
            return self._phasors[name]
        except KeyError:
            raise KeyError(
                f"フェーザ {name!r} は未登録です。先に add() で追加してください"
            ) from None

    def _point(self, p: PointLike) -> complex:
        if isinstance(p, str):
            return self._get(p).tip
        if isinstance(p, tuple):
            return complex(p[0], p[1])
        return complex(p)

    def _format_angle(self, rad: float, precision: Optional[int] = None) -> str:
        if self.angle_unit == "deg":
            value = round(math.degrees(rad), 1 if precision is None else precision)
            return f"{value + 0.0:g}°"
        value = round(rad, 3 if precision is None else precision)
        return f"{value + 0.0:g} rad"

    def _phasor_text(self, p: _Phasor) -> str:
        text = p.label
        if p.scale != 1.0:
            text += f" (×{p.scale:g})"
        if p.show_value:
            ang = self._format_angle(cmath.phase(p.z))
            text += f"\n{abs(p.z):.4g}∠{ang}"
        return text

    def _xy(self, z: complex) -> Tuple[float, float]:
        """複素数 → 軸のデータ座標。"""
        if self.mode == "polar":
            return cmath.phase(z), abs(z)
        return z.real, z.imag

    def _xy_array(self, pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if self.mode == "polar":
            return np.unwrap(np.angle(pts)), np.abs(pts)
        return pts.real, pts.imag

    def _plot_pts(self, ax, pts: np.ndarray, **kwargs) -> None:
        xs, ys = self._xy_array(pts)
        ax.plot(xs, ys, **kwargs)

    def _plot_segment(self, ax, z0: complex, z1: complex, **kwargs) -> None:
        # 極座標でも直線に見えるよう、細かくサンプリングして描く
        t = np.linspace(0.0, 1.0, 96)
        self._plot_pts(ax, z0 + (z1 - z0) * t, **kwargs)

    def _style_context(self):
        font = self.font or find_japanese_font()
        families = [font, "DejaVu Sans"] if font else ["DejaVu Sans"]
        return rc_context(
            {
                "font.family": families,
                "axes.unicode_minus": False,
                "mathtext.fontset": "cm",
            }
        )

    def _all_points(self) -> List[complex]:
        pts: List[complex] = [0j]
        for p in self._phasors.values():
            pts += [p.origin, p.tip]
        for ln in self._lines:
            pts += [ln.start, ln.end]
        for tx in self._texts:
            pts.append(tx.pos)
        for arc in self._arcs:
            pts.append(arc.label_pos)
        return pts

    # ------------------------------------------------------------------ #
    # 内部: 描画
    # ------------------------------------------------------------------ #
    def _build(self, use_pyplot: bool):
        if use_pyplot:
            fig = plt.figure(figsize=self.figsize)
        else:
            fig = Figure(figsize=self.figsize)
        if self.mode == "polar":
            ax = fig.add_subplot(111, projection="polar")
        else:
            ax = fig.add_subplot(111)

        self._setup_axes(ax)

        for ln in self._lines:
            self._plot_segment(
                ax, ln.start, ln.end,
                color=ln.color, linestyle=ln.linestyle,
                linewidth=ln.linewidth, alpha=ln.alpha, zorder=2,
            )
        for arc in self._arcs:
            self._draw_arc(ax, arc)
        for p in self._phasors.values():
            self._draw_phasor(ax, p)
        for tx in self._texts:
            x, y = self._xy(tx.pos)
            ax.text(
                x, y, tx.text, color=tx.color, ha=tx.ha, va=tx.va,
                fontsize=tx.fontsize or self.font_size, zorder=5,
            )

        if self.title:
            ax.set_title(self.title, fontsize=self.font_size + 2, pad=16)
        if self.legend and self._phasors:
            self._draw_legend(ax)
        return fig, ax

    def _setup_axes(self, ax) -> None:
        pts = self._all_points()

        if self.mode == "polar":
            rmax = self.limit or nice_ceil(max(abs(z) for z in pts) * 1.3)
            ax.set_theta_zero_location("E")
            ax.set_theta_direction(1)
            ax.set_rlim(0, rmax)
            ax.set_thetagrids(np.arange(0, 360, self.angle_step))
            ax.grid(self.grid, linestyle=":", alpha=0.7)
            ax.tick_params(labelsize=self.font_size - 2)
            ax.set_axisbelow(True)
            return

        if self.limit:
            xlo = ylo = -self.limit
            xhi = yhi = self.limit
        else:
            xs = [z.real for z in pts]
            ys = [z.imag for z in pts]
            span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
            half = span / 2 + span * 0.28
            cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
            xlo, xhi, ylo, yhi = cx - half, cx + half, cy - half, cy + half
        ax.set_xlim(xlo, xhi)
        ax.set_ylim(ylo, yhi)
        ax.set_aspect("equal", adjustable="box")
        ax.axhline(0, color="0.35", linewidth=0.9, zorder=1)
        ax.axvline(0, color="0.35", linewidth=0.9, zorder=1)
        ax.set_xlabel(self.xlabel, fontsize=self.font_size)
        ax.set_ylabel(self.ylabel, fontsize=self.font_size)
        ax.tick_params(labelsize=self.font_size - 2)
        ax.grid(self.grid, linestyle=":", alpha=0.7)
        ax.set_axisbelow(True)

    def _draw_phasor(self, ax, p: _Phasor) -> None:
        vec = p.vec
        if abs(vec) == 0:
            return

        ax.annotate(
            "",
            xy=self._xy(p.tip),
            xytext=self._xy(p.origin),
            xycoords="data",
            textcoords="data",
            annotation_clip=False,
            zorder=3,
            arrowprops=dict(
                arrowstyle="-|>",
                color=p.color,
                lw=p.linewidth,
                linestyle=p.linestyle,
                alpha=p.alpha,
                shrinkA=0,
                shrinkB=0,
                mutation_scale=18,
            ),
        )

        # ラベルは矢印の延長方向に少しずらして置く(はみ出し・重なり防止)
        ux, uy = (vec / abs(vec)).real, (vec / abs(vec)).imag
        ha = "left" if ux > 0.3 else ("right" if ux < -0.3 else "center")
        va = "bottom" if uy > 0.3 else ("top" if uy < -0.3 else "center")
        ax.annotate(
            self._phasor_text(p),
            xy=self._xy(p.tip),
            xytext=(ux * 7 + p.label_offset[0], uy * 7 + p.label_offset[1]),
            textcoords="offset points",
            ha=ha,
            va=va,
            color=p.color,
            fontsize=self.font_size,
            annotation_clip=False,
            zorder=5,
        )

        if p.components:
            for foot in (complex(p.tip.real, 0.0), complex(0.0, p.tip.imag)):
                self._plot_segment(
                    ax, p.tip, foot,
                    color=p.color, linestyle=":", linewidth=1.0, alpha=0.6, zorder=2,
                )

    def _draw_arc(self, ax, arc: _Arc) -> None:
        if abs(arc.delta) > 1e-9:
            t = np.linspace(0.0, 1.0, 96)
            theta = arc.start_angle + arc.delta * t
            pts = arc.center + arc.radius * np.exp(1j * theta)
            self._plot_pts(
                ax, pts,
                color=arc.color, linestyle=arc.linestyle,
                linewidth=arc.linewidth, zorder=2,
            )
        if arc.text:
            x, y = self._xy(arc.label_pos)
            ax.text(
                x, y, arc.text, color=arc.color, ha="center", va="center",
                fontsize=arc.fontsize or self.font_size - 1,
                bbox=_ARC_LABEL_BBOX, zorder=4,
            )

    def _draw_legend(self, ax) -> None:
        handles = [
            Line2D(
                [0], [0], color=p.color, linestyle=p.linestyle,
                linewidth=p.linewidth, label=p.label,
            )
            for p in self._phasors.values()
        ]
        if self.mode == "polar":
            ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.08))
        else:
            ax.legend(handles=handles, loc="best")
