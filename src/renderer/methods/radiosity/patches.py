"""从共享三角网格构建 Radiosity Patch 集合。

每个三角面对应一个 Patch，直接复用正式面法线和材质索引，不创建另一套场景。
面积、质心和法线采用双精度数组，供 Form Factor 与线性求解共同使用。
"""

from dataclasses import dataclass
import numpy as np

from renderer.geometry.mesh import TriangleMesh


@dataclass(frozen=True, slots=True)
class PatchSet:
    """按面索引对齐的 Patch 几何数组。"""

    centroids: np.ndarray
    normals: np.ndarray
    areas: np.ndarray
    material_indices: np.ndarray


def subdivide_mesh(mesh: TriangleMesh, levels: int) -> TriangleMesh:
    """将每个三角形递归均分为四个共面 Patch。

    参数:
        mesh: 原始共享几何。
        levels: 细分级数，0 返回几何等价副本，2 会把每个面变为 16 个 Patch。
    返回值:
        保持表面形状与逐面材质不变的细分 :class:`TriangleMesh`。
    异常:
        ValueError: ``levels`` 不是非负整数时抛出。
    副作用:
        无；不会修改原网格。
    """

    if not isinstance(levels, int) or isinstance(levels, bool) or levels < 0:
        raise ValueError("levels 必须是非负整数")
    triangles = mesh.triangles.copy()
    materials = mesh.material_indices.copy()
    for _ in range(levels):
        vertex0 = triangles[:, 0]
        vertex1 = triangles[:, 1]
        vertex2 = triangles[:, 2]
        midpoint01 = (vertex0 + vertex1) * 0.5
        midpoint12 = (vertex1 + vertex2) * 0.5
        midpoint20 = (vertex2 + vertex0) * 0.5
        triangles = np.concatenate(
            (
                np.stack((vertex0, midpoint01, midpoint20), axis=1),
                np.stack((midpoint01, vertex1, midpoint12), axis=1),
                np.stack((midpoint20, midpoint12, vertex2), axis=1),
                np.stack((midpoint01, midpoint12, midpoint20), axis=1),
            ),
            axis=0,
        )
        materials = np.tile(materials, 4)
    vertices = triangles.reshape(-1, 3)
    faces = np.arange(len(vertices), dtype=np.int64).reshape(-1, 3)
    return TriangleMesh(vertices, faces, materials)


def build_patches(mesh: TriangleMesh) -> PatchSet:
    """由正式三角网格生成 Patch 几何。

    参数:
        mesh: 共享不可变三角网格。
    返回值:
        与网格面顺序一一对应的 :class:`PatchSet`。
    异常:
        退化面已由 ``TriangleMesh`` 阻止，正常调用不抛出业务异常。
    副作用:
        无。
    """

    triangles = mesh.triangles
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(cross, axis=1)
    return PatchSet(
        centroids=triangles.mean(axis=1),
        normals=cross / lengths[:, None],
        areas=0.5 * lengths,
        material_indices=mesh.material_indices.copy(),
    )
