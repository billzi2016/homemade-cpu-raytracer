"""Rasterization baseline 的平面 Lambert 直接光照。

该着色器故意不发射 Shadow Ray，也不计算反射、折射或间接光。它仅根据三角形
几何法线、材质反照率和点光源平方反比衰减生成可重复的非光追基线。
"""

from __future__ import annotations

import numpy as np

from renderer.lights.point import PointLight
from renderer.materials.base import SurfaceMaterial


def shade_face(
    centroid: np.ndarray,
    normal: np.ndarray,
    material: SurfaceMaterial,
    lights: tuple[PointLight, ...],
    ambient_strength: float = 0.02,
) -> np.ndarray:
    """计算单个面的线性 RGB 平面颜色。

    参数:
        centroid: 世界坐标三角形中心。
        normal: 单位几何法线；双面着色会取光照方向绝对余弦。
        material: 共享表面材质。
        lights: 点光源集合。
        ambient_strength: 非物理可见性基线项，范围 ``[0, 1]``。

    返回值:
        非负有限线性 RGB。

    异常:
        ValueError: 环境项越界或几何退化时抛出。

    副作用:
        无。
    """

    if not 0.0 <= ambient_strength <= 1.0:
        raise ValueError("ambient_strength 必须位于 [0, 1]")
    center = np.asarray(centroid, dtype=np.float64)
    unit_normal = np.asarray(normal, dtype=np.float64)
    length = float(np.linalg.norm(unit_normal))
    if center.shape != (3,) or unit_normal.shape != (3,) or length <= 1e-15:
        raise ValueError("centroid 和 normal 必须是有效三维向量")
    unit_normal = unit_normal / length
    color = material.emission.astype(np.float64, copy=True)
    color += material.albedo * ambient_strength
    for light in lights:
        to_light = light.position - center
        distance_squared = float(np.dot(to_light, to_light))
        if distance_squared <= 1e-15:
            continue
        direction = to_light / np.sqrt(distance_squared)
        cosine = abs(float(np.dot(unit_normal, direction)))
        color += material.albedo * light.intensity * (cosine / distance_squared)
    return np.maximum(color, 0.0)
