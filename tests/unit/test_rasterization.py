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


def test_zbuffer_perspective_interpolates_vertex_colors() -> None:
    """带顶点颜色的正式 Z-Buffer 路径应写出有限连续颜色而非整面常量。"""

    screen = np.array([[1.0, 1.0], [6.0, 1.0], [1.0, 6.0]])
    depth = np.full((8, 8), np.inf)
    faces = np.full((8, 8), -1, dtype=np.int64)
    image = np.zeros((8, 8, 3))
    rasterize_triangle(screen, np.array([2.0, 3.0, 4.0]), 1, depth, faces, np.eye(3), image)

    assert np.all(np.isfinite(image))
    assert np.count_nonzero(image[2, 2]) == 3
    assert not np.array_equal(image[2, 2], image[3, 2])


def test_rasterization_renders_real_cornell_box_with_finite_energy() -> None:
    """正式 Cornell Box 小图应包含多个颜色区域且所有能量非负有限。"""

    image = render_rasterization(create_cornell_box(), 48, 48)

    assert image.shape == (48, 48, 3)
    assert np.all(np.isfinite(image))
    assert np.all(image >= 0.0)
    assert np.count_nonzero(np.linalg.norm(image, axis=2) > 0.0) > 48 * 48 // 4
    # 透视校正顶点光照应形成连续梯度；若退化回逐三角形常量着色，颜色数量会
    # 接近可见面数而远低于该阈值。
    assert np.unique(np.round(image.reshape(-1, 3), 4), axis=0).shape[0] >= 100
