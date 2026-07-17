"""Ray Casting 的正式逐像素渲染入口。

每个像素仅生成一条主射线，命中后计算发光与带硬阴影的直接光。该实现是
Whitted 的直接光基础，但自身不会递归，也不采样任何间接光路。
"""

from __future__ import annotations

import numpy as np

from renderer.core.ray import Ray
from renderer.geometry.intersection import TriangleIntersector
from renderer.methods.ray_casting.shading import shade_direct
from renderer.scenes.scene import Scene


def trace_primary_ray(ray: Ray, scene: Scene, intersector: TriangleIntersector) -> np.ndarray:
    """追踪单条主射线并返回直接线性 RGB。

    参数:
        ray: 世界坐标主射线。
        scene: 正式共享场景。
        intersector: 与 ``scene.mesh`` 对应的共享求交器。

    返回值:
        未命中为零，命中为自发光加硬阴影直接光；形状为 ``(3,)``。

    异常:
        传播公共场景、求交和着色契约的 ``ValueError``。

    副作用:
        无。
    """

    hit = intersector.intersect(ray)
    if hit is None:
        return np.zeros(3, dtype=np.float64)
    material = scene.materials[hit.material_index]
    return shade_direct(hit, material, scene, intersector)


def render_ray_casting(scene: Scene, width: int, height: int) -> np.ndarray:
    """用单次主射线渲染完整图像。

    参数:
        scene: 统一 Cornell Box 或兼容场景。
        width/height: 输出尺寸，单位为像素，必须为正整数。

    返回值:
        形状 ``(height, width, 3)`` 的非负线性 ``float64`` 图像。

    异常:
        ValueError: 尺寸非法或生产契约被违反时抛出。

    副作用:
        无文件或网络访问；当前函数只生成内存图像。
    """

    if width <= 0 or height <= 0:
        raise ValueError("图像宽高必须为正整数")
    intersector = TriangleIntersector(scene.mesh)
    image = np.zeros((height, width, 3), dtype=np.float64)
    for pixel_y in range(height):
        for pixel_x in range(width):
            ray = scene.camera.generate_ray(pixel_x, pixel_y, width, height)
            image[pixel_y, pixel_x] = trace_primary_ray(ray, scene, intersector)
    return image
