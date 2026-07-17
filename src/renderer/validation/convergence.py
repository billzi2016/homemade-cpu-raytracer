"""Monte Carlo 图像误差的正式数值指标。"""

import numpy as np


def mean_squared_error(estimate: object, reference: object) -> float:
    """计算两幅同形有限图像的逐元素均方误差。

    参数:
        estimate: 待评估线性 RGB 图像。
        reference: 使用更高 SPP 生成的同形生产参考图。
    返回值:
        非负有限标量 MSE。
    异常:
        ValueError: 形状不同、数组为空或包含 NaN/Inf 时抛出。
    副作用:
        无。
    """

    left = np.asarray(estimate, dtype=np.float64)
    right = np.asarray(reference, dtype=np.float64)
    if left.shape != right.shape or left.size == 0:
        raise ValueError("estimate 与 reference 必须是同形非空数组")
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise ValueError("MSE 输入不能包含 NaN 或 Inf")
    difference = left - right
    return float(np.mean(difference * difference))
