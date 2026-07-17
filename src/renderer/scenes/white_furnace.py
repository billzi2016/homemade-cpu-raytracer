"""创建能量守恒白炉验证场景。

白炉复用封闭 Cornell 几何，但把所有非发光表面替换为单位白漫反射材质，
供路径积分器在均匀环境辐亮度下验证能量不会增益或丢失。
"""

import numpy as np

from renderer.materials import DiffuseMaterial
from renderer.scenes.cornell_box import create_cornell_box
from renderer.scenes.scene import Scene


def create_white_furnace() -> Scene:
    """返回所有网格面均为单位白漫反射的验证场景，无网络或文件副作用。"""

    source = create_cornell_box()
    white = DiffuseMaterial(np.ones(3))
    materials = tuple(white for _ in source.materials)
    return Scene("white-furnace", source.mesh, materials, source.camera)
