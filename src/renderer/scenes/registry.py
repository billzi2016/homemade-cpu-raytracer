"""场景名称到正式构造器的唯一注册表。"""

from collections.abc import Callable

from renderer.scenes.cornell_box import create_cornell_box
from renderer.scenes.scene import Scene
from renderer.scenes.white_furnace import create_white_furnace


_SCENE_FACTORIES: dict[str, Callable[[int], Scene]] = {
    "cornell-box": lambda sphere_subdivisions: create_cornell_box(
        sphere_subdivisions=sphere_subdivisions
    ),
    "cornell-box-mixed": lambda sphere_subdivisions: create_cornell_box(
        mixed_materials=True,
        sphere_subdivisions=sphere_subdivisions,
    ),
    # 白炉是固定验证夹具，不能被 README 的 Whitted 几何质量参数改变。
    "white-furnace": lambda _sphere_subdivisions: create_white_furnace(),
}


def create_scene(name: str, sphere_subdivisions: int = 2) -> Scene:
    """按稳定名称和球面质量创建场景；未知名称或非法级数明确失败。"""

    try:
        factory = _SCENE_FACTORIES[name]
    except KeyError as error:
        choices = ", ".join(sorted(_SCENE_FACTORIES))
        raise ValueError(f"未知场景 {name!r}；可选值：{choices}") from error
    return factory(sphere_subdivisions)


def scene_names() -> tuple[str, ...]:
    """返回按字典序排列的正式场景名称，无副作用。"""

    return tuple(sorted(_SCENE_FACTORIES))
