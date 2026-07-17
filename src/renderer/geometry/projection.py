"""光栅化使用的世界坐标到屏幕坐标投影。"""

from __future__ import annotations

import math
import numpy as np

from renderer.core.camera import Camera


def project_vertices(vertices: object, camera: Camera, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    """投影世界顶点并返回屏幕 ``(x, y)`` 与正向相机深度。

    位于相机后方的顶点仍返回代数投影，但深度小于等于零，调用方必须裁剪包含
    这些顶点的三角形。尺寸或数组非法时抛出 ``ValueError``，无副作用。
    """

    points = np.asarray(vertices, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.all(np.isfinite(points)):
        raise ValueError("vertices 必须是有限 (N, 3) 数组")
    if width <= 0 or height <= 0:
        raise ValueError("图像宽高必须为正整数")
    right, up, forward = camera.basis()
    relative = points - camera.origin
    x_camera = relative @ right
    y_camera = relative @ up
    depth = relative @ forward
    focal_y = 1.0 / math.tan(math.radians(camera.vertical_fov_degrees) / 2.0)
    focal_x = focal_y / (width / height)
    safe_depth = np.where(np.abs(depth) > 1e-15, depth, np.copysign(1e-15, depth + 1e-30))
    ndc_x = x_camera * focal_x / safe_depth
    ndc_y = y_camera * focal_y / safe_depth
    screen = np.column_stack(((ndc_x + 1.0) * 0.5 * width, (1.0 - ndc_y) * 0.5 * height))
    return screen, depth.copy()
