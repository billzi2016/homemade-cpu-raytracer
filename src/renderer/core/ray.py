"""射线数据结构与参数方程计算。

射线统一使用世界坐标系和双精度数组。构造时会复制并冻结输入，避免调用方随后
修改原数组导致跨进程或递归求交结果悄然变化。本模块不负责求交或射线偏移策略。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from renderer.core.types import Vec3


def _validated_vec3(value: object, field_name: str) -> Vec3:
    """把输入转换为只读、有限的双精度三维向量。

    参数:
        value: 可由 NumPy 转换为数组的向量值。
        field_name: 用于错误消息的字段名称。

    返回值:
        形状为 ``(3,)``、数据独立且不可写的 ``float64`` 数组。

    异常:
        ValueError: 输入形状不是三维向量或包含 NaN/Inf 时抛出。
        TypeError: 输入无法转换为数值数组时由 NumPy 抛出。

    副作用:
        无；返回值不会与调用方输入共享可写内存。
    """

    vector = np.array(value, dtype=np.float64, copy=True)
    if vector.shape != (3,):
        raise ValueError(f"{field_name} 必须是形状为 (3,) 的向量")
    if not np.all(np.isfinite(vector)):
        raise ValueError(f"{field_name} 必须全部为有限数值")
    vector.flags.writeable = False
    return vector


@dataclass(frozen=True, slots=True)
class Ray:
    """世界坐标系中的归一化射线。

    参数:
        origin: 射线起点，单位与场景几何一致。
        direction: 射线方向；构造后自动归一化，因此参数 ``t`` 与场景长度同单位。

    异常:
        ValueError: 起点/方向不是有限三维向量，或方向长度接近零时抛出。

    副作用:
        无；内部数组为独立只读副本。
    """

    origin: Vec3
    direction: Vec3

    def __post_init__(self) -> None:
        """验证起点并把方向归一化为只读向量。

        返回值:
            无。

        异常:
            ValueError: 输入不满足 :class:`Ray` 的几何约束时抛出。

        副作用:
            仅通过冻结数据类允许的底层赋值替换内部副本，不修改调用方数组。
        """

        origin = _validated_vec3(self.origin, "origin")
        direction = _validated_vec3(self.direction, "direction")
        norm = float(np.linalg.norm(direction))
        if norm <= np.finfo(np.float64).eps:
            raise ValueError("direction 长度必须大于浮点精度阈值")

        # 射线方向在构造边界统一归一化，使所有求交器共享 t 的距离语义，避免每个
        # 算法自行判断方向长度并产生不一致的 epsilon 或阴影距离。
        normalized = np.array(direction / norm, dtype=np.float64, copy=True)
        normalized.flags.writeable = False
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "direction", normalized)

    def at(self, distance: float) -> Vec3:
        """计算射线参数方程在指定距离处的点。

        参数:
            distance: 从起点沿归一化方向前进的有符号距离，单位与场景一致。

        返回值:
            可写的世界坐标三维点；返回新数组，不暴露内部只读存储。

        异常:
            ValueError: ``distance`` 为 NaN 或 Inf 时抛出。

        副作用:
            无。
        """

        if not np.isfinite(distance):
            raise ValueError("distance 必须是有限数值")
        return np.asarray(self.origin + float(distance) * self.direction, dtype=np.float64)
