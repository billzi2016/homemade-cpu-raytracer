"""材质被动能量边界的结构化验证。"""

import numpy as np

from renderer.materials.base import SurfaceMaterial


def validate_material_energy(materials: tuple[SurfaceMaterial, ...], tolerance: float = 1e-12) -> dict[str, object]:
    """检查所有被动材质反射/透射通道不超过 1。

    返回包含 ``passed``、最大通道值和材质数量的可序列化字典；容差必须非负。
    自发光不属于被动反射能量，因此不参与该上界检查。
    """

    if tolerance < 0.0:
        raise ValueError("tolerance 不能为负")
    maximum = max((float(np.max(material.albedo)) for material in materials), default=0.0)
    return {"passed": maximum <= 1.0 + tolerance, "max_albedo": maximum, "materials": len(materials)}
