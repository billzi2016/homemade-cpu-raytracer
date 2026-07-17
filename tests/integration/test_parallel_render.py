"""统一 ProcessPoolExecutor 与正式 Tile 渲染集成测试。"""

import numpy as np

from renderer.config import RenderConfig, RenderMethod, RenderQuality
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


def test_parallel_progress_reports_real_completed_tiles(capsys) -> None:
    """启用进度时应由真实完成 Tile 推进到 100%，并写入 stderr。"""

    config = RenderConfig(
        method=RenderMethod.RASTERIZATION,
        width=8,
        height=8,
        workers=1,
        tile_width=4,
        tile_height=4,
    )
    result = render_parallel(config, show_progress=True)
    captured = capsys.readouterr()

    assert result.tiles == 4
    assert "rasterization" in captured.err
    assert "100%" in captured.err


def test_deterministic_supersampling_preserves_requested_output_size() -> None:
    """四样本规则网格只提高确定性方法内部采样，最终图像尺寸必须保持不变。"""

    config = RenderConfig(
        method=RenderMethod.RAY_CASTING,
        width=8,
        height=6,
        workers=1,
        tile_width=4,
        tile_height=3,
        quality=RenderQuality(deterministic_samples_per_pixel=4),
    )
    assert render_parallel(config).image.shape == (6, 8, 3)
