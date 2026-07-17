"""理想无吸收介质材质数据模型。"""

from dataclasses import dataclass
import math

import numpy as np

from renderer.materials.base import SurfaceMaterial, validated_rgb


@dataclass(frozen=True, slots=True)
class DielectricMaterial(SurfaceMaterial):
    """保存透射颜色和折射率；折射率必须为有限正数。"""

    transmittance: np.ndarray
    index_of_refraction: float = 1.5

    def __post_init__(self) -> None:
        """校验透射能量和折射率，无外部副作用。"""

        object.__setattr__(self, "transmittance", validated_rgb(self.transmittance, "transmittance"))
        if not math.isfinite(self.index_of_refraction) or self.index_of_refraction <= 0.0:
            raise ValueError("index_of_refraction 必须是有限正数")

    @property
    def albedo(self) -> np.ndarray:
        """返回只读透射颜色。"""

        return self.transmittance

    @property
    def emission(self) -> np.ndarray:
        """理想介质自身不发光，返回零向量。"""

        return np.zeros(3, dtype=np.float64)

    @property
    def kind(self) -> str:
        """返回稳定标识 ``dielectric``。"""

        return "dielectric"
