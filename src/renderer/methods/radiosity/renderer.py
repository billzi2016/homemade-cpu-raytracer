"""Radiosity 求解、投影和验证元数据的正式入口。"""

from dataclasses import dataclass
import numpy as np

from renderer.geometry import project_vertices
from renderer.methods.radiosity.form_factors import compute_form_factors
from renderer.methods.radiosity.patches import build_patches, subdivide_mesh
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


def render_radiosity(scene: Scene, width: int, height: int, subdivision_levels: int = 2) -> RadiosityResult:
    """求解并渲染纯漫反射场景。

    尺寸必须为正。镜面和玻璃材质不属于 Radiosity 模型，调用方应使用标准漫反射
    Cornell Box；函数输出完整数值证据而不只返回图片。
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
    factors = compute_form_factors(patch_mesh, patches, visibility_mesh=scene.mesh)
    solution = solve_radiosity(patches, scene.materials, factors)
    screen, depths = project_vertices(patch_mesh.vertices, scene.camera, width, height)
    depth_buffer = np.full((height, width), np.inf)
    face_buffer = np.full((height, width), -1, dtype=np.int64)
    for face_index, face in enumerate(patch_mesh.faces):
        if np.any(depths[face] <= 1e-9):
            continue
        rasterize_triangle(screen[face], depths[face], face_index, depth_buffer, face_buffer)
    image = np.zeros((height, width, 3), dtype=np.float64)
    visible = face_buffer >= 0
    image[visible] = solution.radiosity[face_buffer[visible]]
    return RadiosityResult(image, solution.radiosity, factors, solution.residuals)
