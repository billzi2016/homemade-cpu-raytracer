"""点光源数据模型，供直接光方法使用。"""

from dataclasses import dataclass
import numpy as np

from renderer.materials.base import validated_rgb


@dataclass(frozen=True, slots=True)
class PointLight:
    """世界坐标点光源；强度为非负线性 RGB 辐射强度。"""

    position: np.ndarray
    intensity: np.ndarray

    def __post_init__(self) -> None:
        """校验并冻结位置和强度；非法输入抛出 ``ValueError``。"""

        position = np.asarray(self.position, dtype=np.float64).copy()
        if position.shape != (3,) or not np.all(np.isfinite(position)):
            raise ValueError("position 必须是有限三维向量")
        position.flags.writeable = False
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "intensity", validated_rgb(self.intensity, "intensity", upper_bound=None))
