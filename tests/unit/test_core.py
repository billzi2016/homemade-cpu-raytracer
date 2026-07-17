"""射线与公共色彩管线的生产实现测试。

这些测试验证归一化、只读输入隔离、参数方程、色调映射和 sRGB 边界，确保后续
五种方法共享同一数学语义，而不是在测试中重写参考实现。
"""

import numpy as np
import pytest

from renderer.core.color import encode_rgb8, linear_to_srgb, reinhard_tone_map
from renderer.core.ray import Ray


def test_ray_normalizes_direction_and_isolates_input_arrays() -> None:
    """射线应复制输入并让参数距离保持世界长度语义。"""

    origin = np.array([1.0, 2.0, 3.0])
    direction = np.array([0.0, 0.0, -2.0])
    ray = Ray(origin=origin, direction=direction)

    origin[0] = 99.0
    direction[2] = 99.0

    np.testing.assert_allclose(ray.origin, [1.0, 2.0, 3.0])
    np.testing.assert_allclose(ray.direction, [0.0, 0.0, -1.0])
    np.testing.assert_allclose(ray.at(2.5), [1.0, 2.0, 0.5])
    assert not ray.origin.flags.writeable
    assert not ray.direction.flags.writeable


@pytest.mark.parametrize(
    ("origin", "direction"),
    [
        ([0.0, 0.0], [0.0, 0.0, 1.0]),
        ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]),
        ([0.0, np.nan, 0.0], [0.0, 0.0, 1.0]),
    ],
)
def test_ray_rejects_invalid_geometry(origin: object, direction: object) -> None:
    """非法形状、非有限坐标和零方向不能进入求交层。"""

    with pytest.raises(ValueError):
        Ray(origin=origin, direction=direction)  # type: ignore[arg-type]


def test_color_pipeline_preserves_black_and_encodes_hdr_monotonically() -> None:
    """公共显示变换应保持黑色，并随线性能量单调增加。"""

    linear = np.array([[0.0, 0.0, 0.0], [0.18, 1.0, 4.0]])
    encoded = encode_rgb8(linear)

    np.testing.assert_array_equal(encoded[0], [0, 0, 0])
    assert encoded.dtype == np.uint8
    assert int(encoded[1, 0]) < int(encoded[1, 1]) < int(encoded[1, 2])


def test_tone_mapping_and_srgb_match_known_boundaries() -> None:
    """Reinhard 的单位输入应为二分之一，sRGB 暗部应走线性分段。"""

    np.testing.assert_allclose(reinhard_tone_map([1.0, 1.0, 1.0]), [0.5, 0.5, 0.5])
    np.testing.assert_allclose(
        linear_to_srgb([0.0, 0.0031308, 1.0]),
        [0.0, 0.040449936, 1.0],
        atol=1e-9,
    )


def test_color_pipeline_rejects_negative_energy() -> None:
    """负辐射能量必须被明确拒绝，不能在编码时静默截断。"""

    with pytest.raises(ValueError):
        encode_rgb8([-0.01, 0.0, 0.0])
