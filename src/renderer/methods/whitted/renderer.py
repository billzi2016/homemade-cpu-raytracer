"""Whitted 确定性递归光线追踪生产实现。

漫反射面复用 Ray Casting 的正式直接光；镜面和介质分别递归生成理想反射与
Fresnel 分配的反射/折射射线。最大深度是明确终止条件，不存在测试专用旁路。
"""

from __future__ import annotations

import math
import numpy as np

from renderer.core.ray import Ray
from renderer.geometry import TriangleIntersector
from renderer.materials import DielectricMaterial, MirrorMaterial
from renderer.methods.ray_casting.shading import shade_direct
from renderer.methods.whitted.fresnel import schlick_reflectance
from renderer.methods.whitted.optics import reflect, refract
from renderer.scenes.scene import Scene


def trace_whitted(
    ray: Ray,
    scene: Scene,
    intersector: TriangleIntersector,
    depth: int = 0,
    max_depth: int = 6,
    ray_epsilon: float = 1e-5,
) -> np.ndarray:
    """递归追踪单条 Whitted 光线并返回线性 RGB。

    参数:
        ray: 当前世界坐标射线。
        scene/intersector: 共享正式场景及对应求交器。
        depth: 当前递归深度，顶层为 0。
        max_depth: 允许求交和着色的最大深度，必须非负。
        ray_epsilon: 次级射线起点偏移，单位与场景一致。
    返回值:
        非负有限线性 RGB；未命中或超过深度时为零。
    异常:
        ValueError: 深度或 epsilon 非法时抛出。
    副作用:
        无。
    """

    if depth < 0 or max_depth < 0 or depth > max_depth + 1:
        raise ValueError("递归深度参数非法")
    if not math.isfinite(ray_epsilon) or ray_epsilon <= 0.0:
        raise ValueError("ray_epsilon 必须是有限正数")
    if depth > max_depth:
        return np.zeros(3, dtype=np.float64)
    hit = intersector.intersect(ray)
    if hit is None:
        return np.zeros(3, dtype=np.float64)
    material = scene.materials[hit.material_index]
    if not isinstance(material, (MirrorMaterial, DielectricMaterial)):
        return shade_direct(hit, material, scene, intersector, ray_epsilon)
    if depth == max_depth:
        return material.emission.astype(np.float64, copy=True)

    reflected_direction = reflect(ray.direction, hit.normal)
    reflected_ray = Ray(hit.point + hit.normal * ray_epsilon, reflected_direction)
    reflected = trace_whitted(reflected_ray, scene, intersector, depth + 1, max_depth, ray_epsilon)

    if isinstance(material, MirrorMaterial):
        return material.emission + material.reflectance * reflected

    incident_ior = 1.0 if hit.front_face else material.index_of_refraction
    transmitted_ior = material.index_of_refraction if hit.front_face else 1.0
    refracted_direction = refract(ray.direction, hit.normal, incident_ior, transmitted_ior)
    if refracted_direction is None:
        return reflected

    cosine = min(1.0, max(0.0, -float(np.dot(ray.direction, hit.normal))))
    reflection_weight = schlick_reflectance(cosine, incident_ior, transmitted_ior)
    # 折射方向穿过当前着色法线的反侧，因此沿 -normal 偏移，避免立即再次命中
    # 同一三角形。反射和透射 Fresnel 权重之和严格为 1；透射颜色又不超过 1。
    refracted_ray = Ray(hit.point - hit.normal * ray_epsilon, refracted_direction)
    transmitted = trace_whitted(refracted_ray, scene, intersector, depth + 1, max_depth, ray_epsilon)
    result = reflection_weight * reflected
    result += (1.0 - reflection_weight) * material.transmittance * transmitted
    return np.maximum(result, 0.0)


def render_whitted(scene: Scene, width: int, height: int, max_depth: int = 6) -> np.ndarray:
    """渲染完整 Whitted 图像；尺寸或深度非法时抛出 ``ValueError``。"""

    if width <= 0 or height <= 0 or max_depth < 0:
        raise ValueError("图像尺寸必须为正且 max_depth 不能为负")
    intersector = TriangleIntersector(scene.mesh)
    image = np.zeros((height, width, 3), dtype=np.float64)
    for pixel_y in range(height):
        for pixel_x in range(width):
            ray = scene.camera.generate_ray(pixel_x, pixel_y, width, height)
            image[pixel_y, pixel_x] = trace_whitted(ray, scene, intersector, max_depth=max_depth)
    return image
