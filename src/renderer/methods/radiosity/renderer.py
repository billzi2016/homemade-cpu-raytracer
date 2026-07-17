"""Radiosity 求解、投影和验证元数据的正式入口。"""

from dataclasses import dataclass
from collections.abc import Callable
import math
import numpy as np

from renderer.geometry import TriangleMesh, project_vertices
from renderer.methods.radiosity.form_factors import compute_form_factors
from renderer.methods.radiosity.patches import PatchSet, build_patches, subdivide_mesh
from renderer.methods.radiosity.solver import solve_radiosity
from renderer.methods.rasterization.zbuffer import rasterize_triangle
from renderer.scenes.scene import Scene


@dataclass(frozen=True, slots=True)
class RadiosityResult:
    """Radiosity 图像、Patch 解、Form Factor 与求解残差。"""

    image: np.ndarray
    patch_radiosity: np.ndarray
    form_factors: np.ndarray
    residuals: np.ndarray


def _interpolate_patch_vertex_radiance(
    mesh: TriangleMesh,
    patches: PatchSet,
    patch_radiance: np.ndarray,
) -> np.ndarray:
    """按同位置、同材质和同平面汇总 Patch，生成连续顶点辐亮度。

    Radiosity 的未知量仍是逐 Patch 常量；这里仅为最终显示构造经典 Gouraud
    插值值。分组键包含材质和法线，因此墙角、箱体棱边及红绿边界不会互相串色。
    每个 Patch 按真实面积加权，避免大小不同的三角形拥有相同统计权重。
    """

    vertex_colors = np.zeros((len(mesh.vertices), 3), dtype=np.float64)
    accumulations: dict[tuple[object, ...], tuple[np.ndarray, float]] = {}
    vertex_keys: list[tuple[object, ...]] = []
    for face_index, face in enumerate(mesh.faces):
        material = int(mesh.material_indices[face_index])
        normal_key = tuple(np.round(patches.normals[face_index], 12))
        weight = float(patches.areas[face_index])
        for vertex_index in face:
            position_key = tuple(np.round(mesh.vertices[vertex_index], 12))
            key = (material, *normal_key, *position_key)
            weighted, total_weight = accumulations.get(key, (np.zeros(3), 0.0))
            accumulations[key] = (
                weighted + patch_radiance[face_index] * weight,
                total_weight + weight,
            )
            vertex_keys.append(key)
    for vertex_index, key in enumerate(vertex_keys):
        weighted, total_weight = accumulations[key]
        vertex_colors[vertex_index] = weighted / total_weight
    return vertex_colors


def render_radiosity(
    scene: Scene,
    width: int,
    height: int,
    subdivision_levels: int = 2,
    progress_callback: Callable[[int], None] | None = None,
) -> RadiosityResult:
    """求解并渲染纯漫反射场景。

    参数:
        scene: 只在实际引用面上使用漫反射材质的生产场景。
        width/height: 输出像素尺寸，必须为正整数。
        subdivision_levels: 每个三角形递归四分的次数，必须满足 Patch 构造约束。
        progress_callback: 每完成一个源 Patch 的 Form Factor 计算时接收增量 1。
    返回值:
        线性 RGB 图像、Patch 辐射度、Form Factor 矩阵和三通道残差。
    异常:
        ValueError: 尺寸非法、实际使用非漫反射材质或数值求解失败时抛出。
    副作用:
        不写文件；只在调用方提供回调时报告计算进度。
    """

    if width <= 0 or height <= 0:
        raise ValueError("图像宽高必须为正整数")
    if any(material.kind != "diffuse" for material in scene.materials):
        # 标准场景材质表包含未被面引用的镜面/玻璃槽位，因此只检查实际引用面。
        used = {int(index) for index in scene.mesh.material_indices}
        if any(scene.materials[index].kind != "diffuse" for index in used):
            raise ValueError("Radiosity 只支持实际使用的漫反射材质")
    patch_mesh = subdivide_mesh(scene.mesh, subdivision_levels)
    patches = build_patches(patch_mesh)
    factors = compute_form_factors(
        patch_mesh,
        patches,
        visibility_mesh=scene.mesh,
        progress_callback=progress_callback,
    )
    solution = solve_radiosity(patches, scene.materials, factors)
    # 方程解 B 是辐射出射度；显示与其他渲染器共享的线性 RGB 辐亮度需除以 π。
    patch_radiance = solution.radiosity / math.pi
    vertex_radiance = _interpolate_patch_vertex_radiance(patch_mesh, patches, patch_radiance)
    screen, depths = project_vertices(patch_mesh.vertices, scene.camera, width, height)
    depth_buffer = np.full((height, width), np.inf)
    face_buffer = np.full((height, width), -1, dtype=np.int64)
    image = np.zeros((height, width, 3), dtype=np.float64)
    for face_index, face in enumerate(patch_mesh.faces):
        if np.any(depths[face] <= 1e-9):
            continue
        rasterize_triangle(
            screen[face],
            depths[face],
            face_index,
            depth_buffer,
            face_buffer,
            vertex_radiance[face],
            image,
        )
    return RadiosityResult(image, solution.radiosity, factors, solution.residuals)
