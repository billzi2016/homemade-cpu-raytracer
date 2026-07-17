"""程序化生成统一 Cornell Box 及混合材质变体。

场景无需下载。房间和天花板面光源使用显式四边形，两个内部箱体使用 Trimesh
成熟网格生成与变换；五种方法从这里读取同一几何、相机和材质参数。
"""

from __future__ import annotations

import numpy as np
import trimesh

from renderer.core.camera import Camera
from renderer.geometry.mesh import MeshPart, TriangleMesh
from renderer.lights.area import AreaLight
from renderer.lights.point import PointLight
from renderer.materials import DielectricMaterial, DiffuseMaterial, MirrorMaterial, SurfaceMaterial
from renderer.scenes.scene import Scene


def _quad(points: list[list[float]], desired_normal: list[float]) -> trimesh.Trimesh:
    """创建法线朝指定方向的两三角形四边形；退化输入由 Trimesh/NumPy 拒绝。"""

    vertices = np.asarray(points, dtype=np.float64)
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    normal = np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0])
    if float(np.dot(normal, desired_normal)) < 0.0:
        faces = faces[:, ::-1]
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def _box(extents: tuple[float, float, float], center: tuple[float, float, float], angle_degrees: float) -> trimesh.Trimesh:
    """用 Trimesh 创建并绕世界 Y 轴旋转箱体，然后平移至指定中心。"""

    mesh = trimesh.creation.box(extents=extents)
    rotation = trimesh.transformations.rotation_matrix(np.radians(angle_degrees), [0.0, 1.0, 0.0])
    rotation[:3, 3] = np.asarray(center)
    mesh.apply_transform(rotation)
    return mesh


def _sphere(radius: float, center: tuple[float, float, float], subdivisions: int) -> trimesh.Trimesh:
    """用指定级数的 Trimesh Icosphere 创建闭合球体并平移到世界坐标。"""

    mesh = trimesh.creation.icosphere(subdivisions=subdivisions, radius=radius)
    mesh.apply_translation(np.asarray(center, dtype=np.float64))
    return mesh


def create_cornell_box(*, mixed_materials: bool = False, sphere_subdivisions: int = 2) -> Scene:
    """创建标准或镜面/玻璃混合 Cornell Box。

    参数:
        mixed_materials: 为真时两个内部箱体分别使用镜面和玻璃；否则均为白色漫反射。
        sphere_subdivisions: 混合场景 Icosphere 细分级数，必须位于 `[1, 5]`。
    返回值:
        完整、离线可用的 :class:`Scene`。
    异常:
        场景常量受单元测试约束，正常调用不抛出业务异常。
    副作用:
        无网络和文件访问；Trimesh 对象仅在函数内部创建。
    """

    if not isinstance(sphere_subdivisions, int) or isinstance(sphere_subdivisions, bool) or not 1 <= sphere_subdivisions <= 5:
        raise ValueError("sphere_subdivisions 必须位于 [1, 5]")

    white = DiffuseMaterial(np.array([0.75, 0.75, 0.75]))
    red = DiffuseMaterial(np.array([0.75, 0.12, 0.10]))
    green = DiffuseMaterial(np.array([0.12, 0.65, 0.15]))
    light_material = DiffuseMaterial(np.zeros(3), np.array([15.0, 15.0, 15.0]))
    mirror = MirrorMaterial(np.array([0.92, 0.92, 0.92]))
    glass = DielectricMaterial(np.array([0.98, 0.98, 0.98]), 1.5)
    materials: tuple[SurfaceMaterial, ...] = (white, red, green, light_material, mirror, glass)

    parts: list[MeshPart] = [
        MeshPart(_quad([[-1, 0, 0], [1, 0, 0], [1, 0, -2], [-1, 0, -2]], [0, 1, 0]), 0),
        MeshPart(_quad([[-1, 2, -2], [1, 2, -2], [1, 2, 0], [-1, 2, 0]], [0, -1, 0]), 0),
        MeshPart(_quad([[-1, 0, -2], [1, 0, -2], [1, 2, -2], [-1, 2, -2]], [0, 0, 1]), 0),
        MeshPart(_quad([[-1, 0, -2], [-1, 2, -2], [-1, 2, 0], [-1, 0, 0]], [1, 0, 0]), 1),
        MeshPart(_quad([[1, 0, 0], [1, 2, 0], [1, 2, -2], [1, 0, -2]], [-1, 0, 0]), 2),
        MeshPart(_quad([[-0.35, 1.99, -0.75], [0.35, 1.99, -0.75], [0.35, 1.99, -1.25], [-0.35, 1.99, -1.25]], [0, -1, 0]), 3),
    ]
    if mixed_materials:
        # 玻璃长方体会产生复杂棱镜光路，难以直观看出 Snell 折射是否正确；闭合球体
        # 保留真实反射/折射，同时让 Whitted 的镜面和介质效果具有清晰可验证的轮廓。
        parts.extend(
            [
                MeshPart(_sphere(0.34, (-0.38, 0.34, -1.05), sphere_subdivisions), 4, True),
                MeshPart(_sphere(0.38, (0.40, 0.38, -1.35), sphere_subdivisions), 5, True),
            ]
        )
    else:
        parts.extend(
            [
                MeshPart(_box((0.62, 0.65, 0.62), (-0.38, 0.325, -1.05), -18.0), 0),
                MeshPart(_box((0.62, 1.20, 0.62), (0.40, 0.60, -1.35), 16.0), 0),
            ]
        )
    mesh = TriangleMesh.combine(parts)
    # 35° 视场角与相机距离匹配 2×2 的正方形开口，避免旧结果四周出现大块黑框。
    camera = Camera(np.array([0.0, 1.0, 3.2]), np.array([0.0, 1.0, -1.0]), np.array([0.0, 1.0, 0.0]), 35.0)
    # half_u × half_v 指向 -Y，使单面光源朝房间内部发光。
    area_light = AreaLight(np.array([0.0, 1.99, -1.0]), np.array([0.35, 0.0, 0.0]), np.array([0.0, 0.0, 0.25]), np.array([15.0, 15.0, 15.0]))
    # 面光源面积为 4|half_u×half_v|=0.35；用 Le×area=5.25 标定点光强度，
    # 使局部光照方法不再相对 Path Tracing 与 Radiosity 严重过曝。
    point_light = PointLight(np.array([0.0, 1.75, -1.0]), np.array([5.25, 5.25, 5.25]))
    return Scene("cornell-box-mixed" if mixed_materials else "cornell-box", mesh, materials, camera, (area_light,), (point_light,))
