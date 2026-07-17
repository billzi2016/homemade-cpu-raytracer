"""程序化 Cornell Box、白炉场景与注册表公开接口。"""

from renderer.scenes.cornell_box import create_cornell_box
from renderer.scenes.registry import create_scene, scene_names
from renderer.scenes.scene import Scene
from renderer.scenes.white_furnace import create_white_furnace

__all__ = ["Scene", "create_cornell_box", "create_scene", "create_white_furnace", "scene_names"]
