"""共享表面材质公开接口。"""

from renderer.materials.base import SurfaceMaterial
from renderer.materials.dielectric import DielectricMaterial
from renderer.materials.diffuse import DiffuseMaterial
from renderer.materials.mirror import MirrorMaterial

__all__ = ["DielectricMaterial", "DiffuseMaterial", "MirrorMaterial", "SurfaceMaterial"]
