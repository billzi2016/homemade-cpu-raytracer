"""不可变三角网格与 Trimesh 适配。

网格保存共享顶点、三角面和逐面材质索引，是五种方法的唯一几何来源。
Trimesh 负责成熟的网格创建与变换；本模块负责把结果转换为稳定生产契约。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh


@dataclass(frozen=True, slots=True)
class TriangleMesh:
    """只读三角网格；非法形状、索引或退化面会抛出 ``ValueError``。"""

    vertices: np.ndarray
    faces: np.ndarray
    material_indices: np.ndarray

    def __post_init__(self) -> None:
        """复制、校验并冻结网格数组，无外部副作用。"""

        vertices = np.asarray(self.vertices, dtype=np.float64).copy()
        faces = np.asarray(self.faces, dtype=np.int64).copy()
        materials = np.asarray(self.material_indices, dtype=np.int64).copy()
        if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.all(np.isfinite(vertices)):
            raise ValueError("vertices 必须是有限的 (N, 3) 数组")
        if faces.ndim != 2 or faces.shape[1] != 3 or len(faces) == 0:
            raise ValueError("faces 必须是非空 (M, 3) 整数数组")
        if materials.shape != (len(faces),) or np.any(materials < 0):
            raise ValueError("material_indices 必须为每个面提供非负索引")
        if np.any(faces < 0) or np.any(faces >= len(vertices)):
            raise ValueError("faces 包含越界顶点索引")
        triangles = vertices[faces]
        areas2 = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
        if np.any(areas2 <= np.finfo(np.float64).eps):
            raise ValueError("网格不能包含退化三角形")
        for array in (vertices, faces, materials):
            array.flags.writeable = False
        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "faces", faces)
        object.__setattr__(self, "material_indices", materials)

    @property
    def triangles(self) -> np.ndarray:
        """返回形状 ``(M, 3, 3)`` 的三角形坐标副本。"""

        return self.vertices[self.faces]

    @property
    def face_normals(self) -> np.ndarray:
        """返回由顶点绕序决定的单位几何法线。"""

        triangles = self.triangles
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        return normals / np.linalg.norm(normals, axis=1, keepdims=True)

    @classmethod
    def combine(cls, parts: list[tuple[trimesh.Trimesh, int]]) -> "TriangleMesh":
        """组合 Trimesh 部件并分配逐面材质索引。

        参数:
            parts: ``(mesh, material_index)`` 列表；网格必须含三角面。
        返回值:
            合并后的独立 :class:`TriangleMesh`。
        异常:
            ValueError: 列表为空或材质索引非法时抛出。
        副作用:
            无；不会修改传入 Trimesh。
        """

        if not parts:
            raise ValueError("parts 不能为空")
        vertices: list[np.ndarray] = []
        faces: list[np.ndarray] = []
        materials: list[np.ndarray] = []
        offset = 0
        for mesh, material_index in parts:
            if material_index < 0:
                raise ValueError("material_index 不能为负")
            triangulated = mesh.copy()
            vertices.append(np.asarray(triangulated.vertices, dtype=np.float64))
            local_faces = np.asarray(triangulated.faces, dtype=np.int64)
            faces.append(local_faces + offset)
            materials.append(np.full(len(local_faces), material_index, dtype=np.int64))
            offset += len(triangulated.vertices)
        return cls(np.vstack(vertices), np.vstack(faces), np.concatenate(materials))
