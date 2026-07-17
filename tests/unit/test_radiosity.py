"""Radiosity Form Factor、互易性、残差和真实 Cornell Box 渲染测试。"""

import numpy as np

from renderer.methods.radiosity import render_radiosity
from renderer.methods.radiosity.form_factors import compute_form_factors
from renderer.methods.radiosity.patches import build_patches, subdivide_mesh
from renderer.scenes import create_cornell_box


def test_form_factors_are_conservative_and_reciprocal() -> None:
    """封闭 Cornell Box 的离散矩阵必须非负、行和为 1 且满足面积互易。"""

    scene = create_cornell_box()
    patches = build_patches(scene.mesh)
    factors = compute_form_factors(scene.mesh, patches)

    assert np.all(factors >= 0.0)
    np.testing.assert_allclose(factors.sum(axis=1), np.ones(len(factors)), rtol=1e-8, atol=1e-9)
    exchange = patches.areas[:, None] * factors
    np.testing.assert_allclose(exchange, exchange.T, rtol=1e-10, atol=1e-11)


def test_radiosity_solves_and_renders_color_bleeding() -> None:
    """正式场景方程残差应很小，白色面应收到红绿间接能量。"""

    result = render_radiosity(create_cornell_box(), 36, 36, subdivision_levels=1)

    assert result.image.shape == (36, 36, 3)
    assert np.all(np.isfinite(result.image))
    assert np.all(result.image >= 0.0)
    assert float(result.residuals.max()) < 1e-10
    assert np.count_nonzero(result.image) > 36 * 36 // 4
    white_patch_colors = result.patch_radiosity[:6]
    assert np.any(np.abs(white_patch_colors[:, 0] - white_patch_colors[:, 1]) > 1e-6)


def test_radiosity_subdivision_preserves_area_and_materials() -> None:
    """两级细分应产生十六倍 Patch，同时保持总面积与材质覆盖。"""

    mesh = create_cornell_box().mesh
    subdivided = subdivide_mesh(mesh, 2)
    assert len(subdivided.faces) == len(mesh.faces) * 16
    np.testing.assert_allclose(build_patches(subdivided).areas.sum(), build_patches(mesh).areas.sum())
    assert set(subdivided.material_indices.tolist()) == set(mesh.material_indices.tolist())
