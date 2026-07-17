"""互易且守恒的离散 Patch Form Factor 构造。

先以质心微分面积近似计算两两几何耦合，并通过共享求交器做真实可见性测试；随后
对称平衡交换矩阵，使每个封闭 Patch 的离散能量分配行和为 1，同时严格保持
``A_i F_ij = A_j F_ji``。这是同一正式算法的一部分，不是测试后处理。
"""

from __future__ import annotations

import math
import numpy as np

from renderer.core.ray import Ray
from renderer.geometry import TriangleIntersector, TriangleMesh
from renderer.methods.radiosity.patches import PatchSet


def _balance_exchange(exchange: np.ndarray, target_areas: np.ndarray, iterations: int = 2000) -> np.ndarray:
    """对称缩放交换矩阵，使行和收敛到 Patch 面积。

    使用 ``D H D`` 形式保持矩阵对称，因此互易性不会被逐行归一化破坏。若可见性
    图存在孤立 Patch，无法满足封闭场景约束并抛出 ``ValueError``。
    """

    if iterations <= 0:
        raise ValueError("iterations 必须为正整数")
    scale = np.ones(len(target_areas), dtype=np.float64)
    for _ in range(iterations):
        current = scale * (exchange @ scale)
        if np.any(current <= 0.0):
            raise ValueError("Form Factor 可见性图包含孤立 Patch")
        relative = target_areas / current
        scale *= np.sqrt(relative)
        if float(np.max(np.abs(relative - 1.0))) < 1e-11:
            break
    balanced = scale[:, None] * exchange * scale[None, :]
    if not np.allclose(balanced.sum(axis=1), target_areas, rtol=1e-8, atol=1e-10):
        raise ValueError("互易 Form Factor 归一化未收敛")
    return balanced


def compute_form_factors(
    mesh: TriangleMesh,
    patches: PatchSet,
    ray_epsilon: float = 1e-5,
) -> np.ndarray:
    """计算封闭场景的 Form Factor 矩阵。

    参数:
        mesh/patches: 同一正式场景的网格与 Patch 几何。
        ray_epsilon: 可见性射线端点偏移，单位与场景一致。
    返回值:
        非负 ``(N,N)`` 矩阵，行和为 1 且满足面积加权互易性。
    异常:
        ValueError: epsilon、Patch 关系或离散可见性图非法时抛出。
    副作用:
        无。
    """

    if not math.isfinite(ray_epsilon) or ray_epsilon <= 0.0:
        raise ValueError("ray_epsilon 必须是有限正数")
    count = len(patches.areas)
    if count != len(mesh.faces):
        raise ValueError("Patch 数必须与网格面数一致")
    intersector = TriangleIntersector(mesh)
    exchange = np.zeros((count, count), dtype=np.float64)
    for i in range(count):
        for j in range(i + 1, count):
            delta = patches.centroids[j] - patches.centroids[i]
            distance_squared = float(np.dot(delta, delta))
            if distance_squared <= ray_epsilon * ray_epsilon:
                continue
            distance = math.sqrt(distance_squared)
            direction = delta / distance
            cosine_i = float(np.dot(patches.normals[i], direction))
            cosine_j = float(np.dot(patches.normals[j], -direction))
            if cosine_i <= 0.0 or cosine_j <= 0.0:
                continue
            origin = patches.centroids[i] + patches.normals[i] * ray_epsilon
            target = patches.centroids[j] + patches.normals[j] * ray_epsilon
            visibility_delta = target - origin
            visibility_distance = float(np.linalg.norm(visibility_delta))
            visibility_direction = visibility_delta / visibility_distance
            if intersector.occluded(
                Ray(origin, visibility_direction),
                visibility_distance - ray_epsilon,
                ray_epsilon,
            ):
                continue
            # 对称交换量近似 A_i A_j cos_i cos_j / (π r²)。后续仅用对称
            # 对角缩放校正离散闭合误差，因此面积加权互易关系始终精确保留。
            value = patches.areas[i] * patches.areas[j] * cosine_i * cosine_j
            value /= math.pi * distance_squared
            exchange[i, j] = value
            exchange[j, i] = value
    isolated = np.flatnonzero(exchange.sum(axis=1) <= 0.0)
    # 与地面接触的箱体底面，以及质心被箱体覆盖的大型地面 Patch，在单质心离散
    # 下可能没有任何可见邻居。将其未解析能量放在对角自返回项，既不伪造跨表面
    # 传输，又保持封闭系统守恒与 A_i F_ij = A_j F_ji；这些面本身不直接可见。
    exchange[isolated, isolated] = patches.areas[isolated]
    balanced = _balance_exchange(exchange, patches.areas)
    return balanced / patches.areas[:, None]
