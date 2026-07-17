"""五种渲染方法共享的 CPU 并行基础设施。

该包集中定义 Worker 数、底层线程限制、Tile 划分和随机流派生，防止不同算法
各自建立不一致的资源策略。它不包含具体渲染任务或进程池生命周期管理。
"""

from renderer.parallel.resources import available_logical_cpus, compute_worker_count
from renderer.parallel.seeds import derive_stream_seed
from renderer.parallel.thread_limits import configure_worker_thread_limits
from renderer.parallel.tiles import Tile, split_into_tiles

__all__ = [
    "Tile",
    "available_logical_cpus",
    "compute_worker_count",
    "configure_worker_thread_limits",
    "derive_stream_seed",
    "split_into_tiles",
]
