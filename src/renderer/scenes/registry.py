"""场景名称到正式构造器的唯一注册表。"""

from collections.abc import Callable

from renderer.scenes.cornell_box import create_cornell_box
from renderer.scenes.scene import Scene
from renderer.scenes.white_furnace import create_white_furnace


_SCENE_FACTORIES: dict[str, Callable[[], Scene]] = {
    "cornell-box": create_cornell_box,
    "cornell-box-mixed": lambda: create_cornell_box(mixed_materials=True),
    "white-furnace": create_white_furnace,
}


def create_scene(name: str) -> Scene:
    """按稳定名称创建场景；未知名称抛出包含可选值的 ``ValueError``。"""

    try:
        factory = _SCENE_FACTORIES[name]
    except KeyError as error:
        choices = ", ".join(sorted(_SCENE_FACTORIES))
        raise ValueError(f"未知场景 {name!r}；可选值：{choices}") from error
    return factory()


def scene_names() -> tuple[str, ...]:
    """返回按字典序排列的正式场景名称，无副作用。"""

    return tuple(sorted(_SCENE_FACTORIES))
