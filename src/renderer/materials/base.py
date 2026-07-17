"""表面材质公共契约与能量参数校验。

材质只保存线性 RGB 光学参数；具体 BRDF/BTDF 采样属于渲染方法。本模块统一
执行非负、有限和不超过 1 的被动能量约束，防止算法各自放宽规则。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


def validated_rgb(value: object, name: str, *, upper_bound: float | None = 1.0) -> np.ndarray:
    """返回只读线性 RGB；非法形状、非有限、负值或越过上界时抛出 ``ValueError``。"""

    rgb = np.asarray(value, dtype=np.float64).copy()
    if rgb.shape != (3,) or not np.all(np.isfinite(rgb)) or np.any(rgb < 0.0):
        raise ValueError(f"{name} 必须是非负有限 RGB 三维向量")
    if upper_bound is not None and np.any(rgb > upper_bound):
        raise ValueError(f"{name} 每个通道不能大于 {upper_bound}")
    rgb.flags.writeable = False
    return rgb


class SurfaceMaterial(ABC):
    """渲染方法共享的只读表面材质接口。"""

    @property
    @abstractmethod
    def albedo(self) -> np.ndarray:
        """返回不超过 1 的线性 RGB 反射/透射颜色。"""

    @property
    @abstractmethod
    def emission(self) -> np.ndarray:
        """返回线性 RGB 自发光辐亮度；非光源通常为零。"""

    @property
    @abstractmethod
    def kind(self) -> str:
        """返回稳定材质类型标识。"""
