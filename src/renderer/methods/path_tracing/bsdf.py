"""漫反射、理想镜面和理想介质的生产 BSDF 采样。

函数返回已经包含 ``f * cos / pdf`` 的吞吐量权重。对于 delta 材质，离散选择概率
与 Fresnel 权重一致，因此反射分支不重复乘 Fresnel，避免产生系统性变暗。
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np

from renderer.geometry.intersection import HitRecord
from renderer.materials import DielectricMaterial, MirrorMaterial, SurfaceMaterial
from renderer.methods.path_tracing.sampling import cosine_sample_hemisphere
from renderer.methods.whitted.fresnel import schlick_reflectance
from renderer.methods.whitted.optics import reflect, refract


@dataclass(frozen=True, slots=True)
class BsdfSample:
    """一次 BSDF 采样结果：世界方向、吞吐量权重和是否为 delta 事件。"""

    direction: np.ndarray
    weight: np.ndarray
    delta: bool


def lambertian_value(albedo: np.ndarray) -> np.ndarray:
    """返回 Lambert BRDF ``albedo / π``；非法反射率抛出 ``ValueError``。"""

    value = np.asarray(albedo, dtype=np.float64)
    if value.shape != (3,) or np.any(value < 0.0) or np.any(value > 1.0):
        raise ValueError("albedo 必须是 [0, 1] 内的 RGB")
    return value / math.pi


def sample_bsdf(
    incoming_direction: np.ndarray,
    hit: HitRecord,
    material: SurfaceMaterial,
    rng: np.random.Generator,
) -> BsdfSample:
    """按材质采样下一条路径方向并返回无偏吞吐量权重。

    漫反射使用余弦采样，故 ``(albedo/π)*cos/(cos/π)=albedo``；镜面权重为
    反射率；玻璃按 Fresnel 概率选择分支，透射分支再乘材质透射颜色。
    """

    if isinstance(material, MirrorMaterial):
        return BsdfSample(reflect(incoming_direction, hit.normal), material.reflectance.copy(), True)
    if isinstance(material, DielectricMaterial):
        incident_ior = 1.0 if hit.front_face else material.index_of_refraction
        transmitted_ior = material.index_of_refraction if hit.front_face else 1.0
        refracted = refract(incoming_direction, hit.normal, incident_ior, transmitted_ior)
        if refracted is None:
            return BsdfSample(reflect(incoming_direction, hit.normal), np.ones(3), True)
        cosine = min(1.0, max(0.0, -float(np.dot(incoming_direction, hit.normal))))
        fresnel = schlick_reflectance(cosine, incident_ior, transmitted_ior)
        if float(rng.random()) < fresnel:
            return BsdfSample(reflect(incoming_direction, hit.normal), np.ones(3), True)
        return BsdfSample(refracted, material.transmittance.copy(), True)

    direction, pdf = cosine_sample_hemisphere(hit.normal, rng)
    cosine = max(0.0, float(np.dot(hit.normal, direction)))
    if pdf <= 0.0 or cosine <= 0.0:
        raise ValueError("余弦采样产生了零概率或反向方向")
    weight = lambertian_value(material.albedo) * cosine / pdf
    return BsdfSample(direction, weight, False)
