"""带面光源 NEE 和俄罗斯轮盘赌的 PBR 路径积分器。

积分器迭代求解渲染方程：显式采样面光源降低直接光方差，BSDF 采样继续传播
间接路径。发光面只在相机或前一事件为 delta 时直接累计，避免与无 MIS 的 NEE
重复计数；环境光未被 NEE 采样，因此任意未命中路径都可累计环境辐亮度。
"""

from __future__ import annotations

import math
import numpy as np

from renderer.core.ray import Ray
from renderer.geometry import TriangleIntersector
from renderer.materials import DielectricMaterial, MirrorMaterial
from renderer.methods.path_tracing.bsdf import lambertian_value, sample_bsdf
from renderer.scenes.scene import Scene


def _sample_area_lights(
    hit,
    material,
    scene: Scene,
    intersector: TriangleIntersector,
    rng: np.random.Generator,
    ray_epsilon: float,
) -> np.ndarray:
    """对每个矩形面光源取一个均匀样本并返回直接辐亮度估计。"""

    if not scene.area_lights or isinstance(material, (MirrorMaterial, DielectricMaterial)):
        return np.zeros(3, dtype=np.float64)
    result = np.zeros(3, dtype=np.float64)
    brdf = lambertian_value(material.albedo)
    for light in scene.area_lights:
        sample = light.sample(float(rng.random()), float(rng.random()))
        delta = sample - hit.point
        distance_squared = float(np.dot(delta, delta))
        if distance_squared <= ray_epsilon * ray_epsilon:
            continue
        distance = math.sqrt(distance_squared)
        direction = delta / distance
        cosine_surface = max(0.0, float(np.dot(hit.normal, direction)))
        cosine_light = max(0.0, float(np.dot(light.normal, -direction)))
        if cosine_surface <= 0.0 or cosine_light <= 0.0:
            continue
        shadow_ray = Ray(hit.point + hit.normal * ray_epsilon, direction)
        if intersector.occluded(shadow_ray, distance - ray_epsilon, ray_epsilon):
            continue
        # 面积 PDF 为 1/A；转换到立体角后为 r²/(cos_light*A)。代回渲染
        # 方程得到 Le * f * cos_surface * cos_light * A / r²。
        result += light.radiance * brdf * cosine_surface * cosine_light * light.area / distance_squared
    return result


def trace_path(
    ray: Ray,
    scene: Scene,
    intersector: TriangleIntersector,
    rng: np.random.Generator,
    max_depth: int = 8,
    min_rr_depth: int = 3,
    ray_epsilon: float = 1e-5,
) -> np.ndarray:
    """追踪一条 Monte Carlo 路径并返回线性 RGB 样本。

    参数:
        ray: 相机或后续路径射线。
        scene/intersector: 同一正式场景与求交器。
        rng: 当前样本独占随机生成器。
        max_depth: 最大表面事件数，必须为正数。
        min_rr_depth: 开始俄罗斯轮盘赌的深度，范围 ``[0,max_depth]``。
        ray_epsilon: 次级射线偏移，单位与场景一致。
    返回值:
        单路径非负有限线性 RGB 估计。
    异常:
        ValueError: 深度或 epsilon 参数非法时抛出。
    副作用:
        推进 RNG，不写文件、不修改场景。
    """

    if max_depth <= 0 or not 0 <= min_rr_depth <= max_depth:
        raise ValueError("路径深度参数非法")
    if not math.isfinite(ray_epsilon) or ray_epsilon <= 0.0:
        raise ValueError("ray_epsilon 必须是有限正数")
    radiance = np.zeros(3, dtype=np.float64)
    throughput = np.ones(3, dtype=np.float64)
    current_ray = ray
    previous_delta = True
    for depth in range(max_depth):
        hit = intersector.intersect(current_ray)
        if hit is None:
            radiance += throughput * scene.environment_radiance
            break
        material = scene.materials[hit.material_index]
        if depth == 0 or previous_delta:
            radiance += throughput * material.emission
        radiance += throughput * _sample_area_lights(hit, material, scene, intersector, rng, ray_epsilon)
        sample = sample_bsdf(current_ray.direction, hit, material, rng)
        throughput *= sample.weight
        if not np.all(np.isfinite(throughput)) or np.any(throughput < 0.0):
            raise ValueError("路径吞吐量出现负值、NaN 或 Inf")
        if float(throughput.max()) <= 0.0:
            break
        if depth >= min_rr_depth:
            survival = min(0.95, max(0.05, float(throughput.max())))
            if float(rng.random()) >= survival:
                break
            throughput /= survival
        offset_sign = 1.0 if float(np.dot(sample.direction, hit.normal)) > 0.0 else -1.0
        current_ray = Ray(hit.point + offset_sign * hit.normal * ray_epsilon, sample.direction)
        previous_delta = sample.delta
    return np.maximum(radiance, 0.0)
