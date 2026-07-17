"""Radiosity 三通道线性方程组构建与 SciPy 求解。"""

from dataclasses import dataclass
import math
import numpy as np
from scipy.linalg import solve

from renderer.materials.base import SurfaceMaterial
from renderer.methods.radiosity.patches import PatchSet


@dataclass(frozen=True, slots=True)
class RadiositySolution:
    """Patch 辐射度与逐通道相对残差。"""

    radiosity: np.ndarray
    residuals: np.ndarray


def solve_radiosity(
    patches: PatchSet,
    materials: tuple[SurfaceMaterial, ...],
    form_factors: np.ndarray,
) -> RadiositySolution:
    """求解 ``B = E + ρ F B`` 的三个颜色通道。

    反射率来自共享材质且不超过 1；发光来自同一生产材质。矩阵奇异、尺寸不符或
    解出现负值/非有限时抛出 ``ValueError``，不返回看似可用的错误图像。
    """

    count = len(patches.areas)
    factors = np.asarray(form_factors, dtype=np.float64)
    if factors.shape != (count, count) or np.any(factors < 0.0) or not np.all(np.isfinite(factors)):
        raise ValueError("form_factors 必须是非负有限方阵")
    reflectance = np.vstack([materials[index].albedo for index in patches.material_indices])
    # 共享发光材质存储的是辐亮度 Le，而 Radiosity 方程中的 E 是半球积分后的
    # 辐射出射度。理想 Lambert 发光面满足 E = πLe，必须在这里统一单位。
    emission = math.pi * np.vstack([materials[index].emission for index in patches.material_indices])
    radiosity = np.zeros_like(emission)
    residuals = np.zeros(3, dtype=np.float64)
    identity = np.eye(count, dtype=np.float64)
    for channel in range(3):
        matrix = identity - reflectance[:, channel, None] * factors
        radiosity[:, channel] = solve(matrix, emission[:, channel], assume_a="gen", check_finite=True)
        residual = matrix @ radiosity[:, channel] - emission[:, channel]
        denominator = max(float(np.linalg.norm(emission[:, channel])), 1e-15)
        residuals[channel] = float(np.linalg.norm(residual)) / denominator
    if np.any(radiosity < -1e-10) or not np.all(np.isfinite(radiosity)):
        raise ValueError("Radiosity 解包含负能量或非有限数值")
    return RadiositySolution(np.maximum(radiosity, 0.0), residuals)
