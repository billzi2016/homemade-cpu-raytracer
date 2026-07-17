"""渲染方法无关的完整场景容器。"""

from dataclasses import dataclass

from renderer.core.camera import Camera
from renderer.geometry.mesh import TriangleMesh
from renderer.lights.area import AreaLight
from renderer.lights.point import PointLight
from renderer.materials.base import SurfaceMaterial


@dataclass(frozen=True, slots=True)
class Scene:
    """绑定网格、材质、相机与光源的不可变场景。

    构造时验证逐面材质索引；不创建求交器、不写文件，也不修改输入对象。
    """

    name: str
    mesh: TriangleMesh
    materials: tuple[SurfaceMaterial, ...]
    camera: Camera
    area_lights: tuple[AreaLight, ...] = ()
    point_lights: tuple[PointLight, ...] = ()

    def __post_init__(self) -> None:
        """验证名称、材质集合和网格引用；非法关系抛出 ``ValueError``。"""

        if not self.name.strip() or not self.materials:
            raise ValueError("场景名称和材质集合不能为空")
        if int(self.mesh.material_indices.max()) >= len(self.materials):
            raise ValueError("网格引用了不存在的材质")
