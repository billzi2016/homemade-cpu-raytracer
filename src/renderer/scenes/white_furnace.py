"""创建能量守恒白炉验证场景。

白炉把单位反射率白球置于亮度 1 的均匀环境中。余弦采样路径命中白球后再离开
表面时，理论辐亮度仍为 1，因此可直接检测 BRDF/PDF 权重的能量增益或损失。
"""

import numpy as np
import trimesh

from renderer.core.camera import Camera
from renderer.geometry.mesh import TriangleMesh
from renderer.materials import DiffuseMaterial
from renderer.scenes.scene import Scene


def create_white_furnace() -> Scene:
    """返回单位白球与单位环境的验证场景，无网络或文件副作用。"""

    sphere = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    mesh = TriangleMesh.combine([(sphere, 0)])
    white = DiffuseMaterial(np.ones(3))
    camera = Camera(np.array([0.0, 0.0, 3.0]), np.zeros(3), np.array([0.0, 1.0, 0.0]), 40.0)
    return Scene(
        "white-furnace",
        mesh,
        (white,),
        camera,
        environment_radiance=np.ones(3, dtype=np.float64),
    )
