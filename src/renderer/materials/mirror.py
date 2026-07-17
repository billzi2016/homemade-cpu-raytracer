"""理想镜面材质数据模型。"""

from dataclasses import dataclass

import numpy as np

from renderer.materials.base import SurfaceMaterial, validated_rgb


@dataclass(frozen=True, slots=True)
class MirrorMaterial(SurfaceMaterial):
    """保存通道反射率；每通道必须位于 ``[0, 1]``。"""

    reflectance: np.ndarray

    def __post_init__(self) -> None:
        """校验并冻结反射率，无外部副作用。"""

        object.__setattr__(self, "reflectance", validated_rgb(self.reflectance, "reflectance"))

    @property
    def albedo(self) -> np.ndarray:
        """返回只读镜面反射率。"""

        return self.reflectance

    @property
    def emission(self) -> np.ndarray:
        """理想镜面自身不发光，返回零向量。"""

        return np.zeros(3, dtype=np.float64)

    @property
    def kind(self) -> str:
        """返回稳定标识 ``mirror``。"""

        return "mirror"
