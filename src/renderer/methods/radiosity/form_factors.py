"""互易且保守的开放 Cornell Box 离散 Patch Form Factor 构造。

先以质心微分面积近似计算两两几何耦合，再通过共享求交器做真实可见性测试。
Cornell Box 的相机侧是开放的，因此能量可以从开口逃逸：行和必须不超过 1，不能
被强行归一化为 1；交换矩阵始终对称，从而严格保持 ``A_i F_ij = A_j F_ji``。
"""

from __future__ import annotations

import math
from collections.abc import Callable
import numpy as np

from renderer.core.ray import Ray
from renderer.geometry import TriangleIntersector, TriangleMesh
from renderer.methods.radiosity.patches import PatchSet


def compute_form_factors(
    mesh: TriangleMesh,
    patches: PatchSet,
    ray_epsilon: float = 1e-5,
    visibility_mesh: TriangleMesh | None = None,
    progress_callback: Callable[[int], None] | None = None,
) -> np.ndarray:
    """计算相机侧开放场景的 Form Factor 矩阵。

    参数:
        mesh/patches: 同一正式场景的 Patch 网格与 Patch 几何。
        ray_epsilon: 可见性射线端点偏移，单位与场景一致。
        visibility_mesh: 几何等价的原始共享网格；提供后避免细分面增加求交成本。
        progress_callback: 每完成一个源 Patch 时接收增量 1；不提供则完全静默。
    返回值:
        非负 ``(N,N)`` 矩阵，行和不超过 1 且满足面积加权互易性。
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
    intersector = TriangleIntersector(visibility_mesh or mesh)
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
        if progress_callback is not None:
            progress_callback(1)
    factors = exchange / patches.areas[:, None]
    max_row_sum = float(np.max(factors.sum(axis=1), initial=0.0))
    if max_row_sum > 1.0:
        # 质心近似在距离很近的 Patch 上可能略微高估立体角。使用一个全局比例
        # 收缩全部交换量可恢复能量上界，并保持交换矩阵对称；逐行归一化会破坏互易性。
        factors /= max_row_sum * (1.0 + 1e-12)
    return factors
