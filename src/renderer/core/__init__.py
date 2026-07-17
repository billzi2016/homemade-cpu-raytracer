"""渲染方法共享的数学与数据契约。

该包只包含无场景副作用的基础类型、射线和颜色函数，不依赖具体渲染方法，
从而保持依赖方向由高层算法指向稳定公共抽象。
"""

from renderer.core.color import encode_rgb8, linear_to_srgb, reinhard_tone_map
from renderer.core.ray import Ray
from renderer.core.types import FloatArray, Vec3

__all__ = [
    "FloatArray",
    "Ray",
    "Vec3",
    "encode_rgb8",
    "linear_to_srgb",
    "reinhard_tone_map",
]
