"""多 SPP PBR Path Tracing 的正式图像渲染入口。"""

from __future__ import annotations

import numpy as np

from renderer.geometry import TriangleIntersector
from renderer.methods.path_tracing.integrator import trace_path
from renderer.parallel.seeds import derive_stream_seed
from renderer.parallel.tiles import Tile
from renderer.scenes.scene import Scene


def render_path_tracing_tile(
    scene: Scene,
    width: int,
    height: int,
    tile: Tile,
    samples_per_pixel: int,
    seed: int = 20260716,
    max_depth: int = 8,
) -> np.ndarray:
    """以固定 Seed 渲染指定全局 Tile。

    每个像素从基础 Seed 和稳定像素索引派生独立随机流，先抖动相机样本再调用
    同一正式积分器。尺寸、SPP、Seed 或深度非法时抛出 ``ValueError``。
    """

    if width <= 0 or height <= 0 or samples_per_pixel <= 0 or max_depth <= 0:
        raise ValueError("图像尺寸、SPP 和 max_depth 必须为正整数")
    if seed < 0:
        raise ValueError("seed 必须为非负整数")
    if tile.x1 > width or tile.y1 > height:
        raise ValueError("Tile 超出完整图像范围")
    intersector = TriangleIntersector(scene.mesh)
    image = np.zeros((tile.height, tile.width, 3), dtype=np.float64)
    for local_y, pixel_y in enumerate(range(tile.y0, tile.y1)):
        for local_x, pixel_x in enumerate(range(tile.x0, tile.x1)):
            pixel_index = pixel_y * width + pixel_x
            rng = np.random.default_rng(derive_stream_seed(seed, pixel_index))
            accumulated = np.zeros(3, dtype=np.float64)
            for _ in range(samples_per_pixel):
                offset_x, offset_y = rng.random(2)
                ray = scene.camera.generate_ray(pixel_x, pixel_y, width, height, float(offset_x), float(offset_y))
                accumulated += trace_path(ray, scene, intersector, rng, max_depth=max_depth)
            image[local_y, local_x] = accumulated / samples_per_pixel
    return image


def render_path_tracing(
    scene: Scene,
    width: int,
    height: int,
    samples_per_pixel: int,
    seed: int = 20260716,
    max_depth: int = 8,
) -> np.ndarray:
    """渲染完整路径追踪图像，复用正式 Tile 入口。"""

    return render_path_tracing_tile(
        scene,
        width,
        height,
        Tile(0, 0, 0, width, height),
        samples_per_pixel,
        seed,
        max_depth,
    )
