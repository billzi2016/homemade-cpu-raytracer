"""理想镜面反射与 Snell 折射方向计算。

函数只处理归一化方向的确定性几何光学，不决定能量权重或递归终止。入射方向
指向表面，法线必须朝向入射方向的反方向，与共享 ``HitRecord.normal`` 语义一致。
"""

from __future__ import annotations

import math
import numpy as np


def _unit(vector: object, name: str) -> np.ndarray:
    """返回有限单位三维向量；零向量或非法输入抛出 ``ValueError``。"""

    result = np.asarray(vector, dtype=np.float64)
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} 必须是有限三维向量")
    length = float(np.linalg.norm(result))
    if length <= np.finfo(np.float64).eps:
        raise ValueError(f"{name} 不能是零向量")
    return result / length


def reflect(direction: object, normal: object) -> np.ndarray:
    """返回理想镜面单位反射方向。

    参数:
        direction: 指向表面的入射单位方向，可接受非单位输入并自动归一化。
        normal: 朝向入射介质的表面法线，可接受非单位输入。
    返回值:
        满足入射角等于反射角的单位向量。
    异常:
        ValueError: 任一向量非法或退化时抛出。
    副作用:
        无。
    """

    incoming = _unit(direction, "direction")
    surface_normal = _unit(normal, "normal")
    result = incoming - 2.0 * float(np.dot(incoming, surface_normal)) * surface_normal
    return result / np.linalg.norm(result)


def refract(
    direction: object,
    normal: object,
    incident_ior: float,
    transmitted_ior: float,
) -> np.ndarray | None:
    """根据 Snell 定律返回理想折射方向，全反射时返回 ``None``。

    ``normal`` 必须朝向入射介质。两个折射率必须为有限正数；函数不计算 Fresnel
    能量，只返回几何方向，因此不会产生颜色或吞吐量副作用。
    """

    if not math.isfinite(incident_ior) or not math.isfinite(transmitted_ior):
        raise ValueError("折射率必须是有限数值")
    if incident_ior <= 0.0 or transmitted_ior <= 0.0:
        raise ValueError("折射率必须为正数")
    incoming = _unit(direction, "direction")
    surface_normal = _unit(normal, "normal")
    cosine_incident = min(1.0, max(0.0, -float(np.dot(incoming, surface_normal))))
    eta = incident_ior / transmitted_ior
    sine_squared_transmitted = eta * eta * (1.0 - cosine_incident * cosine_incident)
    if sine_squared_transmitted > 1.0:
        return None
    cosine_transmitted = math.sqrt(max(0.0, 1.0 - sine_squared_transmitted))
    result = eta * incoming + (eta * cosine_incident - cosine_transmitted) * surface_normal
    return result / np.linalg.norm(result)
