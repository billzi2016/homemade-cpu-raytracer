"""共享透视相机与主射线生成。

相机采用右手世界坐标系，图像原点位于左上角，像素坐标向右、向下增长。
本模块只定义相机几何，不负责采样器、景深或具体渲染方法。
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from renderer.core.ray import Ray


def _vec3(value: object, name: str) -> np.ndarray:
    """返回有限三维向量副本；形状或数值非法时抛出 ``ValueError``。"""

    result = np.asarray(value, dtype=np.float64).copy()
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} 必须是有限三维向量")
    return result


@dataclass(frozen=True, slots=True)
class Camera:
    """固定姿态的针孔透视相机。

    参数:
        origin: 世界坐标相机位置。
        target: 世界坐标观察点，必须与 ``origin`` 不同。
        up: 近似上方向，不能与观察方向平行。
        vertical_fov_degrees: 垂直视场角，单位为度，范围 ``(0, 180)``。

    异常:
        ValueError: 向量退化、非有限或视场角越界时抛出。

    副作用:
        无；输入在构造时复制为只读数组。
    """

    origin: np.ndarray
    target: np.ndarray
    up: np.ndarray
    vertical_fov_degrees: float = 40.0

    def __post_init__(self) -> None:
        """校验并冻结相机参数；无外部副作用。"""

        origin = _vec3(self.origin, "origin")
        target = _vec3(self.target, "target")
        up = _vec3(self.up, "up")
        forward = target - origin
        if np.linalg.norm(forward) <= np.finfo(np.float64).eps:
            raise ValueError("相机 origin 与 target 不能重合")
        if np.linalg.norm(np.cross(forward, up)) <= np.finfo(np.float64).eps:
            raise ValueError("相机 up 不能与观察方向平行")
        if not math.isfinite(self.vertical_fov_degrees) or not 0.0 < self.vertical_fov_degrees < 180.0:
            raise ValueError("vertical_fov_degrees 必须位于 (0, 180)")
        for value in (origin, target, up):
            value.flags.writeable = False
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "up", up)

    def basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """返回 ``(right, true_up, forward)`` 正交单位基；不修改相机。"""

        forward = self.target - self.origin
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, self.up)
        right = right / np.linalg.norm(right)
        true_up = np.cross(right, forward)
        return right, true_up, forward

    def generate_ray(
        self,
        pixel_x: int,
        pixel_y: int,
        width: int,
        height: int,
        offset_x: float = 0.5,
        offset_y: float = 0.5,
    ) -> Ray:
        """生成穿过指定像素采样点的世界坐标主射线。

        参数:
            pixel_x/pixel_y: 零基像素索引。
            width/height: 图像尺寸，单位为像素。
            offset_x/offset_y: 像素内部采样位置，范围 ``[0, 1]``。

        返回值:
            起点为相机位置的归一化 :class:`Ray`。

        异常:
            ValueError: 尺寸、索引或采样偏移越界时抛出。

        副作用:
            无。
        """

        if width <= 0 or height <= 0:
            raise ValueError("图像宽高必须为正整数")
        if not 0 <= pixel_x < width or not 0 <= pixel_y < height:
            raise ValueError("像素索引越界")
        if not 0.0 <= offset_x <= 1.0 or not 0.0 <= offset_y <= 1.0:
            raise ValueError("像素采样偏移必须位于 [0, 1]")
        right, true_up, forward = self.basis()
        aspect = width / height
        half_height = math.tan(math.radians(self.vertical_fov_degrees) / 2.0)
        half_width = aspect * half_height
        ndc_x = ((pixel_x + offset_x) / width) * 2.0 - 1.0
        ndc_y = 1.0 - ((pixel_y + offset_y) / height) * 2.0
        direction = forward + ndc_x * half_width * right + ndc_y * half_height * true_up
        return Ray(self.origin, direction)
