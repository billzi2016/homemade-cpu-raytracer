"""五种方法共享的正式多进程渲染调度器。

四种图像空间方法按 Tile 分发给 ProcessPoolExecutor；每个 Worker 在导入数值工作
前限制底层线程。Radiosity 需要一次全局 Form Factor 和线性求解，因此保持单次
正式求解，避免每个 Tile 重复建立不同矩阵。
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import time

import numpy as np

from renderer.config import RenderConfig, RenderMethod
from renderer.parallel.thread_limits import configure_worker_thread_limits
from renderer.parallel.tiles import Tile, split_into_tiles


@dataclass(frozen=True, slots=True)
class ParallelRenderResult:
    """线性 RGB 图像与实际资源、耗时元数据。"""

    image: np.ndarray
    workers: int
    tiles: int
    elapsed_seconds: float
    diagnostics: dict[str, object]


@dataclass(frozen=True, slots=True)
class _TileTask:
    """可序列化的 Worker 任务描述。"""

    method: RenderMethod
    scene_name: str
    width: int
    height: int
    tile: Tile
    samples_per_pixel: int
    seed: int
    max_depth: int


def _render_tile(task: _TileTask) -> tuple[Tile, np.ndarray]:
    """在 Worker 中构造正式场景并执行对应生产 Tile 渲染器。"""

    from renderer.methods.path_tracing import render_path_tracing_tile
    from renderer.methods.rasterization import render_rasterization_tile
    from renderer.methods.ray_casting import render_ray_casting_tile
    from renderer.methods.whitted import render_whitted_tile
    from renderer.scenes import create_scene

    scene = create_scene(task.scene_name)
    if task.method == RenderMethod.RASTERIZATION:
        image = render_rasterization_tile(scene, task.width, task.height, task.tile)
    elif task.method == RenderMethod.RAY_CASTING:
        image = render_ray_casting_tile(scene, task.width, task.height, task.tile)
    elif task.method == RenderMethod.WHITTED:
        image = render_whitted_tile(scene, task.width, task.height, task.tile, task.max_depth)
    elif task.method == RenderMethod.PATH_TRACING:
        image = render_path_tracing_tile(
            scene,
            task.width,
            task.height,
            task.tile,
            task.samples_per_pixel,
            task.seed,
            task.max_depth,
        )
    else:
        raise ValueError(f"方法 {task.method} 不支持图像 Tile 调度")
    return task.tile, image


def render_parallel(
    config: RenderConfig,
    samples_per_pixel: int = 32,
    max_depth: int = 8,
) -> ParallelRenderResult:
    """按统一资源策略渲染配置指定的方法。

    返回完整线性图像和真实耗时/Worker 元数据。SPP 与深度必须为正；Radiosity
    额外返回残差和 Form Factor 行和误差。函数会创建子进程但不写输出文件。
    """

    if samples_per_pixel <= 0 or max_depth <= 0:
        raise ValueError("samples_per_pixel 和 max_depth 必须为正整数")
    started = time.perf_counter()
    if config.method == RenderMethod.RADIOSITY:
        from renderer.methods.radiosity import render_radiosity
        from renderer.scenes import create_scene

        result = render_radiosity(create_scene(config.scene), config.width, config.height)
        diagnostics = {
            "residuals": result.residuals.tolist(),
            "form_factor_max_row_error": float(np.max(np.abs(result.form_factors.sum(axis=1) - 1.0))),
        }
        return ParallelRenderResult(result.image, 1, 1, time.perf_counter() - started, diagnostics)

    tiles = split_into_tiles(config.width, config.height, config.tile_width, config.tile_height)
    workers = min(config.resolved_workers(), len(tiles))
    tasks = [
        _TileTask(
            config.method,
            config.scene,
            config.width,
            config.height,
            tile,
            samples_per_pixel,
            config.seed,
            max_depth,
        )
        for tile in tiles
    ]
    image = np.zeros((config.height, config.width, 3), dtype=np.float64)
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=configure_worker_thread_limits,
        initargs=(1,),
    ) as pool:
        futures = [pool.submit(_render_tile, task) for task in tasks]
        for future in as_completed(futures):
            tile, tile_image = future.result()
            image[tile.y0 : tile.y1, tile.x0 : tile.x1] = tile_image
    return ParallelRenderResult(image, workers, len(tiles), time.perf_counter() - started, {})
