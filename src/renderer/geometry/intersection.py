"""共享三角形求交器与命中记录。

生产实现使用向量化 Möller–Trumbore 算法一次检测一条射线与全部三角形，适合
当前小型 Cornell Box。所有光线方法复用本实现，避免交点 epsilon 和最近命中分叉。
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from numba import njit

from renderer.core.ray import Ray
from renderer.geometry.mesh import TriangleMesh


@njit(cache=True)
def _nearest_triangle_hit(
    triangles: np.ndarray,
    origin: np.ndarray,
    direction: np.ndarray,
    t_min: float,
    t_max: float,
) -> tuple[int, float]:
    """用无分配循环返回最近面索引与距离；公开校验由 Python 包装层负责。"""

    closest_index = -1
    closest_distance = t_max
    epsilon = 1e-12
    for index in range(triangles.shape[0]):
        vertex0 = triangles[index, 0]
        edge1 = triangles[index, 1] - vertex0
        edge2 = triangles[index, 2] - vertex0
        pvec = np.cross(direction, edge2)
        determinant = np.dot(edge1, pvec)
        if abs(determinant) <= epsilon:
            continue
        inverse = 1.0 / determinant
        tvec = origin - vertex0
        u = np.dot(tvec, pvec) * inverse
        if u < 0.0 or u > 1.0:
            continue
        qvec = np.cross(tvec, edge1)
        v = np.dot(direction, qvec) * inverse
        if v < 0.0 or u + v > 1.0:
            continue
        distance = np.dot(edge2, qvec) * inverse
        if t_min <= distance <= closest_distance:
            closest_index = index
            closest_distance = distance
    return closest_index, closest_distance


@dataclass(frozen=True, slots=True)
class HitRecord:
    """最近射线命中；距离单位与场景一致，法线始终朝向入射射线。"""

    distance: float
    point: np.ndarray
    normal: np.ndarray
    geometric_normal: np.ndarray
    face_index: int
    material_index: int
    front_face: bool


class TriangleIntersector:
    """不可变网格的统一最近命中与遮挡查询器。"""

    def __init__(self, mesh: TriangleMesh) -> None:
        """预计算三角形边；参数为正式共享网格，无外部副作用。"""

        self._mesh = mesh
        self._triangles = np.ascontiguousarray(mesh.triangles, dtype=np.float64)
        self._normals = mesh.face_normals

    def intersect(self, ray: Ray, t_min: float = 1e-6, t_max: float = math.inf) -> HitRecord | None:
        """返回区间内最近命中，未命中返回 ``None``。

        ``t_min`` 用于抑制自相交，``t_max`` 用于阴影距离；两者必须有限/正序，
        其中 ``t_max`` 允许正无穷。函数只读取预计算数组。
        """

        if not math.isfinite(t_min) or t_min < 0.0 or math.isnan(t_max) or t_max <= t_min:
            raise ValueError("求交距离区间非法")
        face_index, distance = _nearest_triangle_hit(
            self._triangles,
            ray.origin,
            ray.direction,
            t_min,
            t_max,
        )
        if face_index < 0:
            return None
        geometric = self._normals[face_index].copy()
        front_face = float(np.dot(ray.direction, geometric)) < 0.0
        normal = geometric if front_face else -geometric
        return HitRecord(
            distance=float(distance),
            point=ray.at(float(distance)),
            normal=normal.copy(),
            geometric_normal=geometric,
            face_index=face_index,
            material_index=int(self._mesh.material_indices[face_index]),
            front_face=front_face,
        )

    def occluded(self, ray: Ray, max_distance: float, t_min: float = 1e-6) -> bool:
        """判断指定距离前是否存在遮挡；参数非法时抛出 ``ValueError``。"""

        if not math.isfinite(max_distance) or max_distance <= t_min:
            raise ValueError("max_distance 必须是大于 t_min 的有限距离")
        return self.intersect(ray, t_min=t_min, t_max=max_distance) is not None
