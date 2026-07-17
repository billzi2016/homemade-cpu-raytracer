"""矩形面光源几何与均匀采样。"""

from dataclasses import dataclass
import numpy as np

from renderer.materials.base import validated_rgb


@dataclass(frozen=True, slots=True)
class AreaLight:
    """由中心和两条半边向量定义的单面矩形光源。"""

    center: np.ndarray
    half_u: np.ndarray
    half_v: np.ndarray
    radiance: np.ndarray

    def __post_init__(self) -> None:
        """校验几何非退化并冻结数组；非法值抛出 ``ValueError``。"""

        values = []
        for name in ("center", "half_u", "half_v"):
            value = np.asarray(getattr(self, name), dtype=np.float64).copy()
            if value.shape != (3,) or not np.all(np.isfinite(value)):
                raise ValueError(f"{name} 必须是有限三维向量")
            values.append(value)
        center, half_u, half_v = values
        if np.linalg.norm(np.cross(half_u, half_v)) <= 1e-15:
            raise ValueError("面光源两条半边不能共线")
        radiance = validated_rgb(self.radiance, "radiance", upper_bound=None)
        for value in (center, half_u, half_v):
            value.flags.writeable = False
        object.__setattr__(self, "center", center)
        object.__setattr__(self, "half_u", half_u)
        object.__setattr__(self, "half_v", half_v)
        object.__setattr__(self, "radiance", radiance)

    @property
    def normal(self) -> np.ndarray:
        """返回由 ``half_u × half_v`` 决定的单位发光方向。"""

        normal = np.cross(self.half_u, self.half_v)
        return normal / np.linalg.norm(normal)

    @property
    def area(self) -> float:
        """返回矩形面积，单位为场景长度平方。"""

        return float(4.0 * np.linalg.norm(np.cross(self.half_u, self.half_v)))

    def sample(self, sample_u: float, sample_v: float) -> np.ndarray:
        """按 ``[0,1]²`` 均匀样本返回光源世界坐标；越界时抛出 ``ValueError``。"""

        if not 0.0 <= sample_u <= 1.0 or not 0.0 <= sample_v <= 1.0:
            raise ValueError("面光源样本必须位于 [0, 1]")
        return self.center + (2.0 * sample_u - 1.0) * self.half_u + (2.0 * sample_v - 1.0) * self.half_v
