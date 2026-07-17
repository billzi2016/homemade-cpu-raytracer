"""非光追 Rasterization baseline 的生产渲染入口。

渲染器投影共享三角网格、执行 CPU Z-Buffer，并按面写入 Lambert 直接光颜色。
输出保持线性 HDR RGB；PNG 编码由公共输出层统一完成。
"""

from __future__ import annotations

import numpy as np

from renderer.geometry.projection import project_vertices
from renderer.methods.rasterization.shading import shade_face
from renderer.methods.rasterization.zbuffer import rasterize_triangle
from renderer.parallel.tiles import Tile
from renderer.scenes.scene import Scene


def render_rasterization_tile(scene: Scene, width: int, height: int, tile: Tile) -> np.ndarray:
    """使用 CPU 光栅化渲染指定全局 Tile。

    参数:
        scene: 使用共享网格、相机、材质和点光源的正式场景。
        width/height: 完整输出尺寸，单位为像素。
        tile: 位于完整图像范围内的目标半开区域。

    返回值:
        形状 ``(tile.height, tile.width, 3)`` 的非负线性 RGB。

    异常:
        ValueError: 图像尺寸非法或场景几何违反公共契约时抛出。

    副作用:
        无文件或网络访问；只在内存中创建颜色、深度和面索引缓冲。
    """

    if width <= 0 or height <= 0:
        raise ValueError("图像宽高必须为正整数")
    if tile.x1 > width or tile.y1 > height:
        raise ValueError("Tile 超出完整图像范围")
    screen, depths = project_vertices(scene.mesh.vertices, scene.camera, width, height)
    local_screen = screen - np.array([tile.x0, tile.y0], dtype=np.float64)
    depth_buffer = np.full((tile.height, tile.width), np.inf, dtype=np.float64)
    face_buffer = np.full((tile.height, tile.width), -1, dtype=np.int64)
    face_colors = np.zeros((len(scene.mesh.faces), 3), dtype=np.float64)
    triangles = scene.mesh.triangles
    normals = scene.mesh.face_normals

    for face_index, face in enumerate(scene.mesh.faces):
        face_depths = depths[face]
        # 第一版 Cornell Box 完全位于近裁剪面前；若未来场景跨越相机平面，必须
        # 实现正式三角形裁剪，而不是投影负深度顶点产生翻转伪影。
        if np.any(face_depths <= 1e-9):
            continue
        rasterize_triangle(local_screen[face], face_depths, face_index, depth_buffer, face_buffer)
        material = scene.materials[int(scene.mesh.material_indices[face_index])]
        face_colors[face_index] = shade_face(
            triangles[face_index].mean(axis=0),
            normals[face_index],
            material,
            scene.point_lights,
        )

    image = np.zeros((tile.height, tile.width, 3), dtype=np.float64)
    visible = face_buffer >= 0
    image[visible] = face_colors[face_buffer[visible]]
    return image


def render_rasterization(scene: Scene, width: int, height: int) -> np.ndarray:
    """渲染完整光栅化图像；实现复用正式 Tile 路径，无文件副作用。"""

    return render_rasterization_tile(scene, width, height, Tile(0, 0, 0, width, height))
