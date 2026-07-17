"""五种方法共享的正式多进程渲染调度器。

四种图像空间方法按 Tile 分发给 ProcessPoolExecutor；每个 Worker 在导入数值工作
前限制底层线程。Radiosity 需要一次全局 Form Factor 和线性求解，因此保持单次
正式求解，避免每个 Tile 重复建立不同矩阵。
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import math
import time

import numpy as np
from tqdm.auto import tqdm

from renderer.config import RenderConfig, RenderMethod, RenderQuality
from renderer.parallel.thread_limits import configure_worker_thread_limits, worker_thread_environment
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
    quality: RenderQuality


def _downsample_regular_grid(image: np.ndarray, tile: Tile, grid_size: int) -> np.ndarray:
    """把规则高分辨率子像素图按等权盒式滤波还原为目标 Tile。

    输入必须精确覆盖 ``tile.height×grid_size`` 与 ``tile.width×grid_size``；函数
    只改变采样密度，不进行色调映射，因此三种确定性方法保持共享线性颜色语义。
    """

    expected_shape = (tile.height * grid_size, tile.width * grid_size, 3)
    if image.shape != expected_shape:
        raise ValueError(f"超采样 Tile 形状应为 {expected_shape}，实际为 {image.shape}")
    grouped = image.reshape(tile.height, grid_size, tile.width, grid_size, 3)
    return grouped.mean(axis=(1, 3))


def _render_tile(task: _TileTask) -> tuple[Tile, np.ndarray]:
    """在 Worker 中构造正式场景并执行对应生产 Tile 渲染器。"""

    from renderer.methods.path_tracing import render_path_tracing_tile
    from renderer.methods.rasterization import render_rasterization_tile
    from renderer.methods.ray_casting import render_ray_casting_tile
    from renderer.methods.whitted import render_whitted_tile
    from renderer.scenes import create_scene

    scene = create_scene(task.scene_name, sphere_subdivisions=task.quality.sphere_subdivisions)
    grid_size = math.isqrt(task.quality.deterministic_samples_per_pixel)
    if task.method in (
        RenderMethod.RASTERIZATION,
        RenderMethod.RAY_CASTING,
        RenderMethod.WHITTED,
    ):
        render_width = task.width * grid_size
        render_height = task.height * grid_size
        render_tile = Tile(
            task.tile.index,
            task.tile.x0 * grid_size,
            task.tile.y0 * grid_size,
            task.tile.x1 * grid_size,
            task.tile.y1 * grid_size,
        )
    else:
        # Path Tracing 使用自己的 Monte Carlo SPP；不能再套确定性超采样，否则会
        # 隐式成倍增加用户明确固定的路径数量。
        render_width = task.width
        render_height = task.height
        render_tile = task.tile
    if task.method == RenderMethod.RASTERIZATION:
        image = render_rasterization_tile(scene, render_width, render_height, render_tile)
    elif task.method == RenderMethod.RAY_CASTING:
        image = render_ray_casting_tile(scene, render_width, render_height, render_tile)
    elif task.method == RenderMethod.WHITTED:
        image = render_whitted_tile(scene, render_width, render_height, render_tile, task.max_depth)
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
    if task.method != RenderMethod.PATH_TRACING and grid_size > 1:
        image = _downsample_regular_grid(image, task.tile, grid_size)
    return task.tile, image


def render_parallel(
    config: RenderConfig,
    samples_per_pixel: int = 32,
    max_depth: int = 8,
    show_progress: bool = False,
    progress_position: int = 0,
) -> ParallelRenderResult:
    """按统一资源策略渲染配置指定的方法。

    参数:
        config: 已校验的生产渲染配置，包含方法、尺寸、场景和 CPU 资源策略。
        samples_per_pixel: Path Tracing 每像素样本数；其他方法保留该统一参数但不采样。
        max_depth: Whitted 与 Path Tracing 的最大递归或路径深度。
        show_progress: 是否向 stderr 输出真实完成量驱动的 tqdm 进度条。
        progress_position: tqdm 行位置；总进度占第 0 行时，方法进度使用第 1 行。
    返回值:
        完整线性 RGB 图像以及真实耗时、Worker、Tile 和诊断元数据。
    异常:
        ValueError: SPP、深度或渲染方法不合法时抛出；Worker 异常原样传播。
    副作用:
        创建受限数量的子进程；启用进度时写 stderr，但不写任何结果文件。

    Radiosity 额外返回残差和 Form Factor 行和范围。图像空间方法按 Tile、
    Radiosity 按 Form Factor 源 Patch 更新进度，因此默认 ETA 基于真实完成量。
    """

    if samples_per_pixel <= 0 or max_depth <= 0:
        raise ValueError("samples_per_pixel 和 max_depth 必须为正整数")
    started = time.perf_counter()
    if config.method == RenderMethod.RADIOSITY:
        from renderer.methods.radiosity import render_radiosity
        from renderer.scenes import create_scene

        scene = create_scene(config.scene)
        # 正式 Radiosity 默认细分两级，每个原始三角形产生 4² 个 Patch。
        # Form Factor 是主要耗时阶段，因此用源 Patch 数作为真实进度单位和 ETA 基础。
        patch_count = len(scene.mesh.faces) * (4**config.quality.radiosity_subdivision_levels)
        with tqdm(
            total=patch_count,
            desc="Radiosity",
            unit="patch",
            position=progress_position,
            leave=True,
            disable=not show_progress,
            dynamic_ncols=True,
        ) as progress:
            result = render_radiosity(
                scene,
                config.width,
                config.height,
                subdivision_levels=config.quality.radiosity_subdivision_levels,
                progress_callback=progress.update if show_progress else None,
            )
        row_sums = result.form_factors.sum(axis=1)
        diagnostics = {
            "residuals": result.residuals.tolist(),
            "form_factor_min_row_sum": float(np.min(row_sums)),
            "form_factor_max_row_sum": float(np.max(row_sums)),
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
            config.quality,
        )
        for tile in tiles
    ]
    image = np.zeros((config.height, config.width, 3), dtype=np.float64)
    # Spawn 型 Worker 会在 initializer 之前加载 Python 入口模块，因此线程环境和
    # Intel OpenMP 提示控制必须在创建进程池前由父进程设置并让子进程继承。
    with worker_thread_environment(1):
        with ProcessPoolExecutor(
            max_workers=workers,
            initializer=configure_worker_thread_limits,
            initargs=(1,),
        ) as pool:
            futures = [pool.submit(_render_tile, task) for task in tasks]
            with tqdm(
                total=len(futures),
                desc=config.method.value,
                unit="tile",
                position=progress_position,
                leave=True,
                disable=not show_progress,
                dynamic_ncols=True,
            ) as progress:
                for future in as_completed(futures):
                    tile, tile_image = future.result()
                    image[tile.y0 : tile.y1, tile.x0 : tile.x1] = tile_image
                    # 只在主进程聚合完成的 Tile，既保证计数准确，也避免多进程争抢终端。
                    progress.update(1)
    return ParallelRenderResult(image, workers, len(tiles), time.perf_counter() - started, {})
