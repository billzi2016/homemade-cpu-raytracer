"""统一的线性色彩、色调映射和 8 位 PNG 编码函数。

所有渲染方法都在线性 RGB 空间累计能量，并在最终输出阶段调用这里的唯一实现。
本模块不负责曝光自动估计或图片写盘，避免验证数据在保存前被隐式改变。
"""

from __future__ import annotations

import numpy as np

from renderer.core.types import FloatArray


def _validated_rgb(colors: object) -> FloatArray:
    """把颜色输入转换为最后一维为 RGB 的有限双精度数组。

    参数:
        colors: 单个 RGB 向量或任意批次的 RGB 数组。

    返回值:
        最后一维长度为 3 的 ``float64`` 数组副本。

    异常:
        ValueError: 形状不以 RGB 三通道结尾或包含 NaN/Inf 时抛出。
        TypeError: 输入无法转换为数值数组时由 NumPy 抛出。

    副作用:
        无。
    """

    array = np.array(colors, dtype=np.float64, copy=True)
    if array.ndim == 0 or array.shape[-1] != 3:
        raise ValueError("颜色数组最后一维必须是长度为 3 的 RGB")
    if not np.all(np.isfinite(array)):
        raise ValueError("颜色数组不能包含 NaN 或 Inf")
    return array


def reinhard_tone_map(linear_rgb: object) -> FloatArray:
    """使用逐通道 Reinhard 算子压缩非负线性 HDR 颜色。

    参数:
        linear_rgb: 线性 RGB 数组，能量值必须非负。

    返回值:
        与输入形状相同、范围位于 ``[0, 1)`` 的双精度数组。

    异常:
        ValueError: 输入格式非法或包含负能量时抛出。

    副作用:
        无；不会修改输入数组。
    """

    colors = _validated_rgb(linear_rgb)
    if np.any(colors < 0.0):
        raise ValueError("线性 RGB 能量不能为负")
    return colors / (1.0 + colors)


def linear_to_srgb(linear_rgb: object) -> FloatArray:
    """把 ``[0, 1]`` 线性 RGB 转换为标准 sRGB 编码值。

    参数:
        linear_rgb: 已完成色调映射、范围位于 ``[0, 1]`` 的线性 RGB 数组。

    返回值:
        与输入形状相同的 sRGB 双精度数组，范围位于 ``[0, 1]``。

    异常:
        ValueError: 输入格式非法或数值超出 ``[0, 1]`` 时抛出。

    副作用:
        无。
    """

    colors = _validated_rgb(linear_rgb)
    if np.any(colors < 0.0) or np.any(colors > 1.0):
        raise ValueError("linear_to_srgb 输入必须位于 [0, 1]")

    # sRGB 在暗部使用线性段，避免幂函数在零附近放大数值误差；亮部使用标准
    # 2.4 指数曲线。该分段必须作为所有渲染器的唯一颜色编码实现。
    return np.where(
        colors <= 0.0031308,
        12.92 * colors,
        1.055 * np.power(colors, 1.0 / 2.4) - 0.055,
    )


def encode_rgb8(linear_hdr_rgb: object) -> np.ndarray:
    """将非负线性 HDR RGB 编码为适合 PNG 的 8 位数组。

    参数:
        linear_hdr_rgb: 单个或批量线性 HDR RGB 值，允许大于 1，不允许为负。

    返回值:
        与输入形状相同的 ``uint8`` 数组。处理顺序固定为 Reinhard、sRGB、
        四舍五入，确保五种方法采用同一显示变换。

    异常:
        ValueError: 输入格式非法、非有限或包含负能量时抛出。

    副作用:
        无。
    """

    mapped = reinhard_tone_map(linear_hdr_rgb)
    srgb = linear_to_srgb(mapped)
    return np.rint(np.clip(srgb, 0.0, 1.0) * 255.0).astype(np.uint8)
