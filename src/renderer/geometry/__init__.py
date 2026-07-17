"""共享三角网格、投影和求交公开接口。"""

from renderer.geometry.intersection import HitRecord, TriangleIntersector
from renderer.geometry.mesh import TriangleMesh
from renderer.geometry.projection import project_vertices

__all__ = ["HitRecord", "TriangleIntersector", "TriangleMesh", "project_vertices"]
