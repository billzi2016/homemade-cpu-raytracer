"""PBR Path Tracing 公开渲染与单路径积分接口。"""

from renderer.methods.path_tracing.integrator import trace_path
from renderer.methods.path_tracing.renderer import render_path_tracing

__all__ = ["render_path_tracing", "trace_path"]
