"""Rasterization baseline 的正式 Z-Buffer 与 Cornell Box 渲染测试。"""

import numpy as np

from renderer.methods.rasterization import render_rasterization
from renderer.methods.rasterization.zbuffer import rasterize_triangle
from renderer.scenes import create_cornell_box


def test_zbuffer_keeps_nearest_triangle_independent_of_draw_order() -> None:
    """相同覆盖区域中更近三角形必须覆盖更远面。"""

    screen = np.array([[1.0, 1.0], [6.0, 1.0], [1.0, 6.0]])
    depth = np.full((8, 8), np.inf)
    faces = np.full((8, 8), -1, dtype=np.int64)
    rasterize_triangle(screen, np.array([4.0, 4.0, 4.0]), 7, depth, faces)
    rasterize_triangle(screen, np.array([2.0, 2.0, 2.0]), 3, depth, faces)

    assert faces[2, 2] == 3
    assert depth[2, 2] == 2.0


def test_rasterization_renders_real_cornell_box_with_finite_energy() -> None:
    """正式 Cornell Box 小图应包含多个颜色区域且所有能量非负有限。"""

    image = render_rasterization(create_cornell_box(), 48, 48)

    assert image.shape == (48, 48, 3)
    assert np.all(np.isfinite(image))
    assert np.all(image >= 0.0)
    assert np.count_nonzero(np.linalg.norm(image, axis=2) > 0.0) > 48 * 48 // 4
    assert np.unique(np.round(image.reshape(-1, 3), 4), axis=0).shape[0] >= 4
