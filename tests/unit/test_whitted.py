"""Whitted 反射、折射、Fresnel 与混合 Cornell Box 正式测试。"""

import math
import numpy as np

from renderer.methods.whitted import render_whitted
from renderer.methods.whitted.fresnel import schlick_reflectance
from renderer.methods.whitted.optics import reflect, refract
from renderer.scenes import create_cornell_box


def test_reflection_preserves_angle_and_unit_length() -> None:
    """四十五度入射应关于法线对称，并保持单位长度。"""

    direction = np.array([1.0, -1.0, 0.0]) / math.sqrt(2.0)
    result = reflect(direction, np.array([0.0, 1.0, 0.0]))
    np.testing.assert_allclose(result, [1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0), 0.0])
    assert math.isclose(float(np.linalg.norm(result)), 1.0)


def test_refraction_obeys_snell_and_detects_total_internal_reflection() -> None:
    """空气入玻璃应满足 Snell 定律，玻璃大角度出射应发生全反射。"""

    theta_i = math.radians(30.0)
    direction = np.array([math.sin(theta_i), -math.cos(theta_i), 0.0])
    result = refract(direction, [0.0, 1.0, 0.0], 1.0, 1.5)
    assert result is not None
    theta_t = math.asin(float(result[0]))
    assert math.isclose(math.sin(theta_i), 1.5 * math.sin(theta_t), rel_tol=1e-12)

    internal = np.array([math.sin(math.radians(60.0)), -math.cos(math.radians(60.0)), 0.0])
    assert refract(internal, [0.0, 1.0, 0.0], 1.5, 1.0) is None


def test_schlick_is_bounded_and_normal_incidence_matches_r0() -> None:
    """Schlick 权重必须有界，空气玻璃法向反射率应约为 4%。"""

    assert math.isclose(schlick_reflectance(1.0, 1.0, 1.5), 0.04, rel_tol=1e-12)
    assert schlick_reflectance(0.0, 1.0, 1.5) == 1.0


def test_whitted_renders_mixed_cornell_box_without_energy_explosion() -> None:
    """镜面/玻璃混合场景应输出有限非负图像，递归深度增加不得数值爆炸。"""

    scene = create_cornell_box(mixed_materials=True)
    shallow = render_whitted(scene, 28, 28, max_depth=2)
    deep = render_whitted(scene, 28, 28, max_depth=6)

    assert np.all(np.isfinite(deep))
    assert np.all(deep >= 0.0)
    assert np.count_nonzero(deep) > 28 * 28 // 5
    assert float(deep.max()) <= 15.0 + 1e-12
    assert not np.array_equal(shallow, deep)
