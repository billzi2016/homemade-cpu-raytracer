"""生产 MSE 指标的数值契约测试。"""

import numpy as np
import pytest

from renderer.validation.convergence import mean_squared_error


def test_mean_squared_error_matches_analytic_value() -> None:
    """简单数组的 MSE 应等于误差平方平均。"""

    estimate = np.array([0.0, 1.0, 2.0])
    reference = np.array([0.0, 0.0, 0.0])
    assert mean_squared_error(estimate, reference) == pytest.approx(5.0 / 3.0)


def test_mean_squared_error_rejects_shape_mismatch() -> None:
    """不同形状不能通过 NumPy 广播被误当成同一图像。"""

    with pytest.raises(ValueError):
        mean_squared_error(np.zeros((2, 3)), np.zeros((3,)))
