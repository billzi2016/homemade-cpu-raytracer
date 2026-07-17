"""使用正式 Path Tracer 执行白炉能量守恒测试。"""

from dataclasses import dataclass
import numpy as np

from renderer.methods.path_tracing import render_path_tracing
from renderer.scenes import create_white_furnace


@dataclass(frozen=True, slots=True)
class WhiteFurnaceResult:
    """白炉图像、最大绝对误差和通过状态。"""

    image: np.ndarray
    max_absolute_error: float
    passed: bool


def run_white_furnace(
    width: int = 24,
    height: int = 24,
    samples_per_pixel: int = 8,
    tolerance: float = 1e-8,
    seed: int = 20260716,
) -> WhiteFurnaceResult:
    """渲染单位白球/单位环境并与解析值 1 比较。

    余弦采样 Lambert 单位反射率的单路径权重理论上恰为 1，因此容差主要覆盖
    浮点误差而不是用宽松统计阈值掩盖能量错误。
    """

    if tolerance < 0.0:
        raise ValueError("tolerance 不能为负")
    image = render_path_tracing(create_white_furnace(), width, height, samples_per_pixel, seed, max_depth=4)
    error = float(np.max(np.abs(image - 1.0)))
    return WhiteFurnaceResult(image, error, error <= tolerance)
