"""跨进程、跨 Tile 的可复现随机流种子派生。

本模块使用 NumPy SeedSequence 混合基础 Seed 与稳定流索引，避免简单相加导致
相邻 Tile 使用高度相关的伪随机序列。它只派生整数 Seed，不持有全局随机状态。
"""

from __future__ import annotations

import numpy as np


def derive_stream_seed(base_seed: int, stream_index: int) -> int:
    """为指定任务流派生稳定的 64 位无符号 Seed。

    参数:
        base_seed: 一次渲染共享的非负基础 Seed。
        stream_index: Tile 或其他任务的非负稳定索引。

    返回值:
        可传递给 ``numpy.random.default_rng`` 的 Python 整数，范围为 64 位无符号值。

    异常:
        ValueError: 任一参数不是非负整数时抛出。

    副作用:
        无；不读取或修改 NumPy 全局随机状态。
    """

    for name, value in (("base_seed", base_seed), ("stream_index", stream_index)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} 必须是非负整数")

    # SeedSequence 会把两个整数作为独立熵分量混合；即使 stream_index 相邻，
    # 生成状态也不会退化为相邻 Seed 的简单线性关系。
    sequence = np.random.SeedSequence([base_seed, stream_index])
    return int(sequence.generate_state(1, dtype=np.uint64)[0])
