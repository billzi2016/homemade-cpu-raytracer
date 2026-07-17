"""项目范围内统一使用的 NumPy 数组类型别名。

本模块只改善类型提示的可读性，不尝试在静态类型系统中编码所有数组形状。
具体函数仍需在运行时验证形状、有限性和坐标语义，不能仅依赖类型别名保证正确性。
"""

from typing import TypeAlias

import numpy as np
import numpy.typing as npt


FloatArray: TypeAlias = npt.NDArray[np.float64]
"""统一双精度浮点数组类型，用于几何和能量计算。"""

Vec3: TypeAlias = npt.NDArray[np.float64]
"""形状为 ``(3,)`` 的三维向量；具体函数负责执行形状校验。"""
