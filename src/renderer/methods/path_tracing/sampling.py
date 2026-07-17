"""Path Tracing 使用的余弦加权半球采样。

采样器接收显式 NumPy Generator，不读取全局随机状态。返回方向和与其严格匹配的
立体角 PDF，确保 BRDF、余弦项和 PDF 能在积分器中形成无偏吞吐量。
"""

from __future__ import annotations

import math
import numpy as np


def cosine_sample_hemisphere(normal: object, rng: np.random.Generator) -> tuple[np.ndarray, float]:
    """围绕指定法线生成余弦加权单位方向。

    参数:
        normal: 世界坐标表面法线，可接受非单位有限三维向量。
        rng: 当前路径独占的 NumPy 随机数生成器。
    返回值:
        ``(direction, pdf)``，其中 PDF 为 ``cos(theta) / π``，单位为逆立体角。
    异常:
        ValueError: 法线非法或退化时抛出。
    副作用:
        推进传入 RNG 状态，不访问全局随机状态。
    """

    unit_normal = np.asarray(normal, dtype=np.float64)
    if unit_normal.shape != (3,) or not np.all(np.isfinite(unit_normal)):
        raise ValueError("normal 必须是有限三维向量")
    length = float(np.linalg.norm(unit_normal))
    if length <= np.finfo(np.float64).eps:
        raise ValueError("normal 不能是零向量")
    unit_normal = unit_normal / length
    u1, u2 = rng.random(2)
    radius = math.sqrt(u1)
    phi = 2.0 * math.pi * u2
    local_x = radius * math.cos(phi)
    local_y = radius * math.sin(phi)
    local_z = math.sqrt(max(0.0, 1.0 - u1))

    helper = np.array([0.0, 1.0, 0.0]) if abs(unit_normal[1]) < 0.999 else np.array([1.0, 0.0, 0.0])
    tangent = np.cross(helper, unit_normal)
    tangent /= np.linalg.norm(tangent)
    bitangent = np.cross(unit_normal, tangent)
    direction = local_x * tangent + local_y * bitangent + local_z * unit_normal
    direction /= np.linalg.norm(direction)
    cosine = max(0.0, float(np.dot(direction, unit_normal)))
    return direction, cosine / math.pi
