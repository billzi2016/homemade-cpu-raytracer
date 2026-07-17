"""经典递归 Whitted Ray Tracing 公开接口。"""

from renderer.methods.whitted.renderer import render_whitted, trace_whitted

__all__ = ["render_whitted", "trace_whitted"]
