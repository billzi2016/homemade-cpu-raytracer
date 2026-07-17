"""漫反射全局光照 Radiosity 公开接口。"""

from renderer.methods.radiosity.renderer import RadiosityResult, render_radiosity

__all__ = ["RadiosityResult", "render_radiosity"]
