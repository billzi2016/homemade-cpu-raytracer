"""Ray Casting 直接光、硬阴影与正式 Cornell Box 渲染测试。"""

import numpy as np

from renderer.core.ray import Ray
from renderer.geometry import TriangleIntersector
from renderer.methods.ray_casting import render_ray_casting, trace_primary_ray
from renderer.scenes import create_cornell_box


def test_primary_ray_returns_black_on_miss_and_light_on_emitter() -> None:
    """未命中必须为黑色，直接命中天花板发光面必须返回自发光。"""

    scene = create_cornell_box()
    intersector = TriangleIntersector(scene.mesh)
    miss = trace_primary_ray(Ray([0.0, 1.0, 1.0], [0.0, 0.0, 1.0]), scene, intersector)
    emitter = trace_primary_ray(Ray([0.0, 1.0, -1.0], [0.0, 1.0, 0.0]), scene, intersector)

    np.testing.assert_array_equal(miss, np.zeros(3))
    assert np.all(emitter >= np.array([15.0, 15.0, 15.0]))


def test_ray_casting_renders_hard_shadowed_cornell_box() -> None:
    """正式 Cornell Box 小图应具有有限非负直接光和明显亮度变化。"""

    image = render_ray_casting(create_cornell_box(), 40, 40)
    luminance = image.mean(axis=2)

    assert image.shape == (40, 40, 3)
    assert np.all(np.isfinite(image))
    assert np.all(image >= 0.0)
    assert np.count_nonzero(luminance > 0.0) > 40 * 40 // 5
    assert float(luminance.max()) > float(np.median(luminance[luminance > 0.0])) * 2.0
