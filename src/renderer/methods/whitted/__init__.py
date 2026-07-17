"""经典递归 Whitted Ray Tracing 公开接口。"""

from renderer.methods.whitted.renderer import render_whitted, render_whitted_tile, trace_whitted

__all__ = ["render_whitted", "render_whitted_tile", "trace_whitted"]
