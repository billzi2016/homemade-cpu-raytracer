"""Ray Casting 的 Lambert 直接光与硬阴影。

本模块通过共享求交器发射有限距离 Shadow Ray，使用 ``albedo / π`` 的 Lambert
BRDF、余弦项和平方反比衰减。它不递归生成反射、折射或间接光线。
"""

from __future__ import annotations

import math
import numpy as np

from renderer.core.ray import Ray
from renderer.geometry.intersection import HitRecord, TriangleIntersector
from renderer.materials.base import SurfaceMaterial
from renderer.scenes.scene import Scene


def shade_direct(
    hit: HitRecord,
    material: SurfaceMaterial,
    scene: Scene,
    intersector: TriangleIntersector,
    ray_epsilon: float = 1e-5,
) -> np.ndarray:
    """计算一次命中的点光源直接辐亮度。

    参数:
        hit: 共享求交器产生的最近命中。
        material: 命中面的公共材质。
        scene: 提供正式点光源的场景。
        intersector: 同一场景网格的求交器，用于硬阴影查询。
        ray_epsilon: 阴影射线起点偏移，单位与场景长度一致，必须为正数。

    返回值:
        非负有限线性 RGB，包含材质自发光和所有可见点光源贡献。

    异常:
        ValueError: epsilon 非正或光源几何产生非法距离时抛出。

    副作用:
        无。
    """

    if not math.isfinite(ray_epsilon) or ray_epsilon <= 0.0:
        raise ValueError("ray_epsilon 必须是有限正数")
    radiance = material.emission.astype(np.float64, copy=True)
    for light in scene.point_lights:
        to_light = light.position - hit.point
        distance_squared = float(np.dot(to_light, to_light))
        if distance_squared <= ray_epsilon * ray_epsilon:
            continue
        distance = math.sqrt(distance_squared)
        direction = to_light / distance
        cosine = max(0.0, float(np.dot(hit.normal, direction)))
        if cosine <= 0.0:
            continue

        # 沿朝向入射射线的着色法线偏移起点，并把最大距离缩短 epsilon，避免把
        # 光源位置之后的几何误判为遮挡，也避免浮点误差让表面遮挡自身。
        shadow_origin = hit.point + hit.normal * ray_epsilon
        shadow_ray = Ray(shadow_origin, direction)
        if intersector.occluded(shadow_ray, max_distance=distance - ray_epsilon, t_min=ray_epsilon):
            continue

        brdf = material.albedo / math.pi
        radiance += brdf * light.intensity * (cosine / distance_squared)
    return np.maximum(radiance, 0.0)
