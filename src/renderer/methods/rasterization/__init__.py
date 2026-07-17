"""非光线追踪 Rasterization baseline 公开接口。"""

from renderer.methods.rasterization.renderer import render_rasterization, render_rasterization_tile

__all__ = ["render_rasterization", "render_rasterization_tile"]
