"""PBR 采样、能量、白炉与真实 Cornell Box 路径追踪测试。"""

import math
import numpy as np

from renderer.methods.path_tracing import render_path_tracing
from renderer.methods.path_tracing.bsdf import lambertian_value
from renderer.methods.path_tracing.sampling import cosine_sample_hemisphere
from renderer.scenes import create_cornell_box
from renderer.validation import run_white_furnace, validate_material_energy


def test_cosine_sampling_pdf_matches_generated_direction() -> None:
    """采样方向必须位于正半球，返回 PDF 必须等于 cos/π。"""

    normal = np.array([0.0, 1.0, 0.0])
    direction, pdf = cosine_sample_hemisphere(normal, np.random.default_rng(7))
    cosine = float(np.dot(direction, normal))
    assert cosine > 0.0
    assert math.isclose(float(np.linalg.norm(direction)), 1.0)
    assert math.isclose(pdf, cosine / math.pi, rel_tol=1e-12)


def test_lambertian_brdf_and_materials_are_energy_bounded() -> None:
    """Lambert BRDF 半球积分对应 albedo，正式 Cornell 材质不超过单位能量。"""

    albedo = np.array([0.8, 0.5, 0.2])
    np.testing.assert_allclose(lambertian_value(albedo) * math.pi, albedo)
    report = validate_material_energy(create_cornell_box(mixed_materials=True).materials)
    assert report["passed"] is True
    assert float(report["max_albedo"]) <= 1.0


def test_white_furnace_preserves_unit_radiance() -> None:
    """单位白材质在单位均匀环境中必须与背景不可区分。"""

    result = run_white_furnace(width=14, height=14, samples_per_pixel=3)
    assert result.passed
    assert result.max_absolute_error <= 1e-8


def test_path_tracing_renders_real_cornell_indirect_light_reproducibly() -> None:
    """固定 Seed 的正式 Cornell 渲染必须可复现、有限且包含非零间接能量。"""

    scene = create_cornell_box()
    first = render_path_tracing(scene, 18, 18, samples_per_pixel=3, seed=11, max_depth=5)
    repeated = render_path_tracing(scene, 18, 18, samples_per_pixel=3, seed=11, max_depth=5)

    np.testing.assert_array_equal(first, repeated)
    assert np.all(np.isfinite(first))
    assert np.all(first >= 0.0)
    assert np.count_nonzero(first) > 18 * 18 // 4
