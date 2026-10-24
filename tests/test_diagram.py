import cmath
import math

import pytest

import phasorplot as pp
from phasorplot import PhasorDiagram


@pytest.mark.parametrize("mode", ["phasor", "polar", "フェーザ", "極座標"])
def test_save_png(tmp_path, mode):
    d = PhasorDiagram(mode=mode, show_values=True, legend=True)
    d.add("V", 100, 0).add("I", 5, -30, scale=15, components=True)
    d.add_angle("V", "I", label=r"$\varphi$")
    d.add_line("V", "I")
    d.add_text((10, 10), "memo")
    out = d.save(tmp_path / "sub" / "out.png", dpi=50)
    assert out.exists() and out.stat().st_size > 0


def test_invalid_mode():
    with pytest.raises(ValueError):
        PhasorDiagram(mode="unknown")


def test_duplicate_name():
    d = PhasorDiagram().add("V", 1, 0)
    with pytest.raises(ValueError):
        d.add("V", 2, 0)


def test_unknown_reference():
    d = PhasorDiagram().add("V", 1, 0)
    with pytest.raises(KeyError):
        d.add_angle("V", "X")


def test_radian_input():
    d = PhasorDiagram(angle_unit="rad").add("V", 2, math.pi / 2)
    assert cmath.isclose(d._phasors["V"].z, 2j, abs_tol=1e-12)


def test_sum_and_origin_chain():
    d = PhasorDiagram()
    d.add("A", 3, 0).add("B", 4, 90, origin="A").add_sum("S", ["A", "B"])
    assert cmath.isclose(d._phasors["B"].origin, 3 + 0j)
    assert cmath.isclose(d._phasors["S"].z, 3 + 4j)
    assert cmath.isclose(d._phasors["B"].tip, d._phasors["S"].tip)


def test_difference():
    d = PhasorDiagram()
    d.add("Va", 100, 0).add("Vb", 100, -120).add_difference("Vab", "Va", "Vb")
    assert math.isclose(abs(d._phasors["Vab"].z), 100 * math.sqrt(3), rel_tol=1e-9)
    assert math.isclose(math.degrees(cmath.phase(d._phasors["Vab"].z)), 30, abs_tol=1e-9)


def test_sum_scale_mismatch():
    d = PhasorDiagram().add("A", 1, 0).add("B", 1, 90, scale=2)
    with pytest.raises(ValueError):
        d.add_sum("S", ["A", "B"])


def test_angle_text():
    d = PhasorDiagram().add("V", 100, 0).add("I", 5, -30)
    d.add_angle("V", "I", label="φ")
    assert d._arcs[0].text == "φ = 30°"
    d.add_angle("V", "I", signed=True, show_value=True)
    assert d._arcs[1].text == "-30°"


def test_one_shot_plot(tmp_path):
    d = pp.plot(
        {"V": (100, 0), "I": (5, -30, {"scale": 10}), "Z": 3 + 4j},
        mode="polar",
        save=tmp_path / "x.png",
        dpi=50,
    )
    assert (tmp_path / "x.png").exists()
    assert set(d._phasors) == {"V", "I", "Z"}


def test_render_returns_figure():
    fig, ax = PhasorDiagram().add("V", 1, 0).render()
    assert fig is not None and ax is not None
