"""统一 ProcessPoolExecutor 与正式 Tile 渲染集成测试。"""

import numpy as np

from renderer.config import RenderConfig, RenderMethod
from renderer.parallel.executor import render_parallel
from renderer.scenes import create_cornell_box
from renderer.methods.ray_casting import render_ray_casting


def test_parallel_tiles_equal_serial_production_render() -> None:
    """两 Worker Tile 结果必须逐值等于同一生产 Ray Casting 完整入口。"""

    config = RenderConfig(
        method=RenderMethod.RAY_CASTING,
        width=16,
        height=12,
        workers=2,
        tile_width=8,
        tile_height=6,
    )
    parallel = render_parallel(config)
    serial = render_ray_casting(create_cornell_box(), 16, 12)

    np.testing.assert_array_equal(parallel.image, serial)
    assert parallel.workers == 2
    assert parallel.tiles == 4
    assert parallel.elapsed_seconds > 0.0
