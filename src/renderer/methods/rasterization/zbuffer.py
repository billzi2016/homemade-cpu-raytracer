"""CPU 三角形覆盖与 Z-Buffer 更新。

函数使用像素中心采样、重心坐标和倒数深度插值。它只负责可见性，不知道场景、
材质或光源，从而让光栅化器的深度规则能够独立验证并保持单一职责。
"""

from __future__ import annotations

import numpy as np


def _edge(a: np.ndarray, b: np.ndarray, point_x: float, point_y: float) -> float:
    """计算二维有向边函数；输入单位为屏幕像素，无副作用。"""

    return float((point_x - a[0]) * (b[1] - a[1]) - (point_y - a[1]) * (b[0] - a[0]))


def rasterize_triangle(
    screen_vertices: np.ndarray,
    depths: np.ndarray,
    face_index: int,
    depth_buffer: np.ndarray,
    face_buffer: np.ndarray,
) -> int:
    """把一个屏幕三角形写入共享深度与面索引缓冲。

    参数:
        screen_vertices: 形状 ``(3, 2)`` 的屏幕坐标，单位为像素。
        depths: 三个正向相机空间深度。
        face_index: 成功深度测试后写入的非负面索引。
        depth_buffer: 形状 ``(H, W)`` 的可写浮点缓冲，初始值通常为正无穷。
        face_buffer: 同形状可写整数缓冲，未命中值通常为 ``-1``。

    返回值:
        本次调用实际更新的像素数量。

    异常:
        ValueError: 输入形状、缓冲关系、索引或深度非法时抛出。

    副作用:
        就地更新两个缓冲；不会修改顶点和深度输入。
    """

    vertices = np.asarray(screen_vertices, dtype=np.float64)
    z = np.asarray(depths, dtype=np.float64)
    if vertices.shape != (3, 2) or z.shape != (3,) or not np.all(np.isfinite(vertices)):
        raise ValueError("三角形屏幕坐标或深度形状非法")
    if np.any(z <= 0.0) or not np.all(np.isfinite(z)):
        raise ValueError("光栅化深度必须是有限正数")
    if depth_buffer.ndim != 2 or face_buffer.shape != depth_buffer.shape:
        raise ValueError("深度缓冲和面缓冲必须是相同二维形状")
    if face_index < 0:
        raise ValueError("face_index 不能为负")

    height, width = depth_buffer.shape
    min_x = max(0, int(np.floor(vertices[:, 0].min())))
    max_x = min(width - 1, int(np.ceil(vertices[:, 0].max())))
    min_y = max(0, int(np.floor(vertices[:, 1].min())))
    max_y = min(height - 1, int(np.ceil(vertices[:, 1].max())))
    area = _edge(vertices[0], vertices[1], vertices[2, 0], vertices[2, 1])
    if abs(area) <= 1e-12 or min_x > max_x or min_y > max_y:
        return 0

    inverse_depth = 1.0 / z
    updated = 0
    for pixel_y in range(min_y, max_y + 1):
        sample_y = pixel_y + 0.5
        for pixel_x in range(min_x, max_x + 1):
            sample_x = pixel_x + 0.5
            w0 = _edge(vertices[1], vertices[2], sample_x, sample_y) / area
            w1 = _edge(vertices[2], vertices[0], sample_x, sample_y) / area
            w2 = 1.0 - w0 - w1
            # 同时接受顺时针和逆时针三角形；归一化后的重心坐标只需全部非负。
            if min(w0, w1, w2) < -1e-12:
                continue
            interpolated_inverse = w0 * inverse_depth[0] + w1 * inverse_depth[1] + w2 * inverse_depth[2]
            if interpolated_inverse <= 0.0:
                continue
            depth = 1.0 / interpolated_inverse
            if depth < depth_buffer[pixel_y, pixel_x]:
                depth_buffer[pixel_y, pixel_x] = depth
                face_buffer[pixel_y, pixel_x] = face_index
                updated += 1
    return updated
