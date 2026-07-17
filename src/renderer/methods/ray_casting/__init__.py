"""单次主射线与硬阴影 Ray Casting 公开接口。"""

from renderer.methods.ray_casting.renderer import render_ray_casting, render_ray_casting_tile, trace_primary_ray

__all__ = ["render_ray_casting", "render_ray_casting_tile", "trace_primary_ray"]
