"""并行资源、线程环境、Tile 和随机流的正式实现测试。

测试覆盖纯函数边界与确定性，不启动伪造 Worker，也不复制调度算法。实际进程池
集成测试将在渲染调度器落地后调用相同的生产 Tile 和 Seed 模块。
"""

import os
import pytest

from renderer.parallel.resources import compute_worker_count
from renderer.parallel.seeds import derive_stream_seed
from renderer.parallel.thread_limits import worker_thread_environment
from renderer.parallel.tiles import Tile, split_into_tiles


@pytest.mark.parametrize(
    ("logical_count", "cpu_percent", "expected"),
    [
        (1, 90.0, 1),
        (2, 90.0, 1),
        (8, 90.0, 7),
        (10, 90.0, 9),
        (16, 50.0, 8),
        (16, 100.0, 15),
    ],
)
def test_compute_worker_count_respects_capacity_and_reserved_core(
    logical_count: int,
    cpu_percent: float,
    expected: int,
) -> None:
    """自动模式应使用指定容量，并在多核机器上保留一个核心。"""

    assert compute_worker_count(cpu_percent=cpu_percent, logical_count=logical_count) == expected


def test_explicit_worker_count_takes_priority_without_oversubscription() -> None:
    """显式 Worker 覆盖百分比，但不能超过逻辑核心总数。"""

    assert compute_worker_count(10.0, explicit_workers=6, logical_count=8) == 6
    assert compute_worker_count(10.0, explicit_workers=12, logical_count=8) == 8


@pytest.mark.parametrize(
    "arguments",
    [
        {"cpu_percent": 0.0, "logical_count": 8},
        {"cpu_percent": float("nan"), "logical_count": 8},
        {"cpu_percent": 90.0, "logical_count": 0},
        {"cpu_percent": 90.0, "explicit_workers": 0, "logical_count": 8},
    ],
)
def test_compute_worker_count_rejects_invalid_resources(arguments: dict[str, object]) -> None:
    """不合法资源配置应明确失败，不能静默退化为任意 Worker 数。"""

    with pytest.raises(ValueError):
        compute_worker_count(**arguments)  # type: ignore[arg-type]


def test_tiles_cover_every_pixel_exactly_once() -> None:
    """非整除图像应由边缘 Tile 完整覆盖，且像素无重叠。"""

    width, height = 70, 50
    tiles = split_into_tiles(width, height, tile_width=32, tile_height=24)
    covered = {
        (x, y)
        for tile in tiles
        for y in range(tile.y0, tile.y1)
        for x in range(tile.x0, tile.x1)
    }

    assert sum(tile.pixel_count for tile in tiles) == width * height
    assert len(covered) == width * height
    assert tiles[-1] == Tile(index=8, x0=64, y0=48, x1=70, y1=50)


def test_stream_seeds_are_reproducible_and_distinct() -> None:
    """相同基础 Seed/索引必须稳定，不同索引必须产生不同随机流 Seed。"""

    first = derive_stream_seed(20260716, 7)
    repeated = derive_stream_seed(20260716, 7)
    neighbor = derive_stream_seed(20260716, 8)

    assert first == repeated
    assert first != neighbor
    assert 0 <= first < 2**64


def test_worker_environment_silences_intel_info_and_restores_parent() -> None:
    """子进程环境应关闭 Intel 信息提示，并在进程池上下文后恢复父进程。"""

    original_warning = os.environ.get("KMP_WARNINGS")
    original_threads = os.environ.get("NUMBA_NUM_THREADS")
    with worker_thread_environment(1):
        assert os.environ["KMP_WARNINGS"] == "0"
        assert os.environ["NUMBA_NUM_THREADS"] == "1"
    assert os.environ.get("KMP_WARNINGS") == original_warning
    assert os.environ.get("NUMBA_NUM_THREADS") == original_threads
