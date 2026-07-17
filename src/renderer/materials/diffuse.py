"""Lambertian 漫反射材质数据模型。"""

from dataclasses import dataclass, field

import numpy as np

from renderer.materials.base import SurfaceMaterial, validated_rgb


@dataclass(frozen=True, slots=True)
class DiffuseMaterial(SurfaceMaterial):
    """保存漫反射率和可选自发光辐亮度；构造非法能量时抛出 ``ValueError``。"""

    reflectance: np.ndarray
    emitted_radiance: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))

    def __post_init__(self) -> None:
        """校验反射率不超过 1；发光允许高动态范围且必须非负。"""

        object.__setattr__(self, "reflectance", validated_rgb(self.reflectance, "reflectance"))
        object.__setattr__(
            self,
            "emitted_radiance",
            validated_rgb(self.emitted_radiance, "emitted_radiance", upper_bound=None),
        )

    @property
    def albedo(self) -> np.ndarray:
        """返回只读漫反射率，无副作用。"""

        return self.reflectance

    @property
    def emission(self) -> np.ndarray:
        """返回只读自发光辐亮度，无副作用。"""

        return self.emitted_radiance

    @property
    def kind(self) -> str:
        """返回稳定标识 ``diffuse``。"""

        return "diffuse"
