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
