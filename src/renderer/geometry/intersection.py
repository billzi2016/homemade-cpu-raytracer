"""共享三角形求交器与命中记录。

生产实现使用向量化 Möller–Trumbore 算法一次检测一条射线与全部三角形，适合
当前小型 Cornell Box。所有光线方法复用本实现，避免交点 epsilon 和最近命中分叉。
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from renderer.core.ray import Ray
from renderer.geometry.mesh import TriangleMesh


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
        triangles = mesh.triangles
        self._v0 = triangles[:, 0]
        self._edge1 = triangles[:, 1] - triangles[:, 0]
        self._edge2 = triangles[:, 2] - triangles[:, 0]
        self._normals = mesh.face_normals

    def intersect(self, ray: Ray, t_min: float = 1e-6, t_max: float = math.inf) -> HitRecord | None:
        """返回区间内最近命中，未命中返回 ``None``。

        ``t_min`` 用于抑制自相交，``t_max`` 用于阴影距离；两者必须有限/正序，
        其中 ``t_max`` 允许正无穷。函数只读取预计算数组。
        """

        if not math.isfinite(t_min) or t_min < 0.0 or math.isnan(t_max) or t_max <= t_min:
            raise ValueError("求交距离区间非法")
        directions = np.broadcast_to(ray.direction, self._edge2.shape)
        pvec = np.cross(directions, self._edge2)
        determinant = np.einsum("ij,ij->i", self._edge1, pvec)
        valid = np.abs(determinant) > 1e-12
        inverse = np.zeros_like(determinant)
        inverse[valid] = 1.0 / determinant[valid]
        tvec = ray.origin - self._v0
        u = np.einsum("ij,ij->i", tvec, pvec) * inverse
        valid &= (u >= 0.0) & (u <= 1.0)
        qvec = np.cross(tvec, self._edge1)
        v = np.einsum("ij,ij->i", directions, qvec) * inverse
        valid &= (v >= 0.0) & ((u + v) <= 1.0)
        distance = np.einsum("ij,ij->i", self._edge2, qvec) * inverse
        valid &= (distance >= t_min) & (distance <= t_max)
        indices = np.flatnonzero(valid)
        if len(indices) == 0:
            return None
        face_index = int(indices[np.argmin(distance[indices])])
        geometric = self._normals[face_index].copy()
        front_face = float(np.dot(ray.direction, geometric)) < 0.0
        normal = geometric if front_face else -geometric
        return HitRecord(
            distance=float(distance[face_index]),
            point=ray.at(float(distance[face_index])),
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
