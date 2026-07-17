"""统一相机、材质、Cornell Box、投影与求交生产实现测试。

测试直接创建正式程序化场景并调用共享几何模块，不使用下载资产、Mock 或测试专用
求交逻辑，确保后续五种方法建立在同一可验证场景契约上。
"""

import numpy as np
import pytest

from renderer.core.camera import Camera
from renderer.core.ray import Ray
from renderer.geometry import TriangleIntersector, project_vertices
from renderer.materials import DiffuseMaterial
from renderer.scenes import create_cornell_box, create_scene, create_white_furnace, scene_names


def test_camera_center_ray_points_at_target() -> None:
    """奇数尺寸中央像素应精确沿相机观察方向。"""

    camera = Camera(np.array([0.0, 0.0, 1.0]), np.zeros(3), np.array([0.0, 1.0, 0.0]), 60.0)
    ray = camera.generate_ray(1, 1, 3, 3)
    np.testing.assert_allclose(ray.direction, [0.0, 0.0, -1.0], atol=1e-12)


def test_projection_places_target_on_image_center() -> None:
    """观察目标投影应位于屏幕中心且具有正深度。"""

    camera = Camera(np.array([0.0, 0.0, 1.0]), np.zeros(3), np.array([0.0, 1.0, 0.0]), 60.0)
    screen, depth = project_vertices(np.array([[0.0, 0.0, 0.0]]), camera, 640, 480)
    np.testing.assert_allclose(screen[0], [320.0, 240.0], atol=1e-12)
    np.testing.assert_allclose(depth, [1.0])


def test_cornell_box_is_offline_complete_and_intersectable() -> None:
    """正式 Cornell Box 应含房间、光源和箱体，并被中央主射线命中。"""

    scene = create_cornell_box()
    assert scene.name == "cornell-box"
    assert len(scene.mesh.faces) == 36
    assert len(scene.materials) == 6
    assert len(scene.area_lights) == 1
    assert scene.area_lights[0].normal[1] < -0.999
    ray = scene.camera.generate_ray(255, 255, 512, 512)
    hit = TriangleIntersector(scene.mesh).intersect(ray)
    assert hit is not None
    assert hit.distance > 0.0
    assert 0 <= hit.material_index < len(scene.materials)
    assert float(np.dot(ray.direction, hit.normal)) <= 0.0


def test_intersector_supports_miss_and_finite_shadow_distance() -> None:
    """朝外射线应未命中，朝后墙射线应在给定距离内产生遮挡。"""

    scene = create_cornell_box()
    intersector = TriangleIntersector(scene.mesh)
    assert intersector.intersect(Ray([0.0, 1.0, 1.0], [0.0, 0.0, 1.0])) is None
    assert intersector.occluded(Ray([0.0, 1.0, -1.0], [0.0, 0.0, -1.0]), 1.1)


def test_material_energy_bounds_are_enforced() -> None:
    """被动漫反射率任一通道超过 1 必须在材质边界被拒绝。"""

    with pytest.raises(ValueError):
        DiffuseMaterial(np.array([1.01, 0.5, 0.5]))


def test_scene_registry_and_white_furnace_use_physical_production_scene() -> None:
    """注册表应完整，白炉应由单位白物体和单位均匀环境构成。"""

    assert scene_names() == ("cornell-box", "cornell-box-mixed", "white-furnace")
    assert create_scene("cornell-box-mixed").name == "cornell-box-mixed"
    furnace = create_white_furnace()
    assert furnace.name == "white-furnace"
    assert len(furnace.mesh.faces) > 0
    np.testing.assert_array_equal(furnace.environment_radiance, np.ones(3))
    assert all(np.array_equal(material.albedo, np.ones(3)) for material in furnace.materials)


def test_mixed_cornell_box_uses_closed_mirror_and_glass_spheres() -> None:
    """Whitted 变体应包含独立镜面/玻璃球，而不是产生棱镜歧义的玻璃箱。"""

    standard = create_cornell_box()
    mixed = create_cornell_box(mixed_materials=True)
    assert len(mixed.mesh.faces) > len(standard.mesh.faces)
    assert 4 in mixed.mesh.material_indices
    assert 5 in mixed.mesh.material_indices
    assert np.any(mixed.mesh.smooth_faces)


def test_mixed_sphere_subdivision_controls_mesh_density() -> None:
    """提高 Icosphere 级数应增加真实几何面数，且不会改变标准盒面数。"""

    coarse = create_cornell_box(mixed_materials=True, sphere_subdivisions=1)
    fine = create_cornell_box(mixed_materials=True, sphere_subdivisions=3)
    assert len(fine.mesh.faces) > len(coarse.mesh.faces)
    assert len(create_cornell_box(sphere_subdivisions=3).mesh.faces) == 36
