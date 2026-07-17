"""进程 Worker 内部的数学库线程限制。

渲染器使用多进程并行；若每个进程再让 BLAS、NumExpr 或 Numba 启动全部线程，
会形成严重过度订阅。本模块应作为进程池 initializer 调用，在 Worker 导入重型数值
模块前把常见线程后端统一限制为指定值。它不创建进程池，也不修改父进程配置。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os


_THREAD_ENVIRONMENT_KEYS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "NUMBA_NUM_THREADS",
)

_FIXED_WORKER_ENVIRONMENT = {
    # Intel OpenMP 仍会从部分依赖内部调用已弃用的 omp_set_nested。该信息不影响
    # 线程限制或数值结果；在子进程加载运行库之前关闭其信息级提示，避免每个
    # Worker 重复污染 tqdm。Python 异常和其他库的 stderr 不受影响。
    "KMP_WARNINGS": "0",
}


def _set_worker_environment(threads_per_worker: int) -> dict[str, str | None]:
    """设置可由新 Worker 继承的线程环境，并返回完整旧值快照。"""

    managed_keys = (*_THREAD_ENVIRONMENT_KEYS, *_FIXED_WORKER_ENVIRONMENT)
    previous = {key: os.environ.get(key) for key in managed_keys}
    value = str(threads_per_worker)
    for key in _THREAD_ENVIRONMENT_KEYS:
        os.environ[key] = value
    os.environ.update(_FIXED_WORKER_ENVIRONMENT)
    return previous


@contextmanager
def worker_thread_environment(threads_per_worker: int = 1) -> Iterator[None]:
    """在进程池创建期间设置可继承环境，并在退出时恢复父进程。

    参数:
        threads_per_worker: 新 Worker 的底层线程上限，必须为正整数。
    返回值:
        上下文管理器不产生业务值。
    异常:
        ValueError: 线程数不是正整数时抛出。
    副作用:
        上下文存续期间修改父进程环境变量；退出时逐项恢复原值或删除新增键。
    """

    if (
        not isinstance(threads_per_worker, int)
        or isinstance(threads_per_worker, bool)
        or threads_per_worker <= 0
    ):
        raise ValueError("threads_per_worker 必须是正整数")
    previous = _set_worker_environment(threads_per_worker)
    try:
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def configure_worker_thread_limits(threads_per_worker: int = 1) -> dict[str, str | None]:
    """限制当前 Worker 内常见数值后端的线程数。

    参数:
        threads_per_worker: 每个进程允许的底层线程数，必须为正整数；多进程渲染
            默认使用 1，避免 ``进程数 × 库线程数`` 过度订阅。

    返回值:
        修改前的环境变量快照，键覆盖所有受管理后端；调用方可将其写入诊断报告。

    异常:
        ValueError: 参数不是正整数时抛出。

    副作用:
        修改当前进程的线程相关环境变量；若 Numba 已导入，同时更新其线程池。
        该函数设计为 Worker 初始化器，不应在运行中的父进程临时调用。
    """

    if (
        not isinstance(threads_per_worker, int)
        or isinstance(threads_per_worker, bool)
        or threads_per_worker <= 0
    ):
        raise ValueError("threads_per_worker 必须是正整数")

    previous = _set_worker_environment(threads_per_worker)

    # Numba 若已初始化线程池，仅修改环境变量不会生效。这里使用公开 API 同步
    # 当前 Worker；导入失败表示该可选运行时不可用，不影响其他后端的限制。
    try:
        import numba

        numba.set_num_threads(threads_per_worker)
    except ImportError:
        pass

    return previous
