"""逻辑 CPU 探测与正式 Worker 数计算。

本模块是整个项目 CPU 资源配置的唯一事实来源。默认策略按逻辑核心的 90%
计算，并尽可能保留一个核心给操作系统；它只计算容量，不声称瞬时监控值精确为 90%。
"""

from __future__ import annotations

import math
import os

import psutil


def available_logical_cpus() -> int:
    """返回当前进程可见的逻辑 CPU 数。

    返回值:
        至少为 ``1`` 的逻辑核心数量。优先使用 psutil，无法探测时回退到
        :func:`os.cpu_count`，两者都未知时安全回退为 1。

    异常:
        无；探测失败通过保守回退处理。

    副作用:
        只读取操作系统 CPU 信息。
    """

    detected = psutil.cpu_count(logical=True)
    if detected is None:
        detected = os.cpu_count()
    return max(1, int(detected or 1))


def compute_worker_count(
    cpu_percent: float = 90.0,
    explicit_workers: int | None = None,
    logical_count: int | None = None,
) -> int:
    """依据 Spec 计算进程池 Worker 数。

    参数:
        cpu_percent: 未显式指定 Worker 时使用的逻辑核心百分比，范围 ``(0, 100]``。
        explicit_workers: 用户显式请求的 Worker 数；存在时优先，但不会超过核心数。
        logical_count: 已知逻辑核心数；为 ``None`` 时探测当前机器。

    返回值:
        范围为 ``[1, logical_count]`` 的 Worker 数。自动模式在多核机器上最多使用
        ``logical_count - 1``，确保至少保留一个逻辑核心。

    异常:
        ValueError: 百分比、Worker 数或逻辑核心数不合法时抛出。

    副作用:
        仅在未提供 ``logical_count`` 时读取操作系统 CPU 信息。
    """

    if not math.isfinite(cpu_percent) or not 0.0 < cpu_percent <= 100.0:
        raise ValueError("cpu_percent 必须是位于 (0, 100] 的有限数值")

    total = available_logical_cpus() if logical_count is None else logical_count
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        raise ValueError("logical_count 必须是正整数")

    if explicit_workers is not None:
        if (
            not isinstance(explicit_workers, int)
            or isinstance(explicit_workers, bool)
            or explicit_workers <= 0
        ):
            raise ValueError("explicit_workers 必须是正整数或 None")
        return min(explicit_workers, total)

    requested = max(1, math.floor(total * cpu_percent / 100.0))
    # 单核机器无法同时保留一个核心并完成工作，因此保持 1；多核机器即使配置
    # 100% 也保留一个核心，遵循 Spec 的交互性和温度风险约束。
    automatic_cap = 1 if total == 1 else total - 1
    return min(requested, automatic_cap)
