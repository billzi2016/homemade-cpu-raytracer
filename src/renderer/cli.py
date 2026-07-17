"""CPU 渲染器的正式命令行入口。

当前工程骨架提供 ``system-info`` 命令，用于报告实际逻辑核心数和按照 Spec
计算出的 Worker 数。后续渲染命令将在同一解析器中接入生产渲染器；本模块不会
维护仅供测试或演示的第二套执行路径。
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from renderer import __version__
from renderer.parallel.resources import available_logical_cpus, compute_worker_count


def build_parser() -> argparse.ArgumentParser:
    """创建命令行解析器。

    返回值:
        配置完成的 :class:`argparse.ArgumentParser`。调用方可以继续解析真实
        命令行，也可在测试中传入显式参数列表；两种方式使用完全相同的解析器。

    异常:
        本函数只构造解析器，不读取外部状态，因此不会主动抛出业务异常。

    副作用:
        无。
    """

    parser = argparse.ArgumentParser(
        prog="homemade-renderer",
        description="在统一 Cornell Box 中比较五种纯 CPU 渲染方法。",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)
    system_parser = subparsers.add_parser(
        "system-info",
        help="输出 CPU 资源探测结果和正式 Worker 配置。",
    )
    system_parser.add_argument(
        "--cpu-percent",
        type=float,
        default=90.0,
        help="用于计算 Worker 数的逻辑 CPU 百分比，范围为 (0, 100]。",
    )
    system_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="显式 Worker 数；提供后优先于 --cpu-percent，但仍不超过逻辑核心数。",
    )
    return parser


def _run_system_info(cpu_percent: float, workers: int | None) -> int:
    """执行 CPU 资源报告命令。

    参数:
        cpu_percent: 允许使用的逻辑 CPU 百分比，单位为百分比。
        workers: 用户显式指定的进程数；为 ``None`` 时按百分比计算。

    返回值:
        成功时返回进程退出码 ``0``。

    异常:
        ValueError: 百分比或显式 Worker 数不在合法范围时抛出。

    副作用:
        向标准输出写入一行 UTF-8 JSON，不修改文件或系统状态。
    """

    logical_cpus = available_logical_cpus()
    resolved_workers = compute_worker_count(
        cpu_percent=cpu_percent,
        explicit_workers=workers,
        logical_count=logical_cpus,
    )
    report = {
        "logical_cpus": logical_cpus,
        "cpu_percent": cpu_percent,
        "workers": resolved_workers,
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """解析参数并执行正式子命令。

    参数:
        argv: 不含程序名的参数序列。为 ``None`` 时读取真实命令行参数。

    返回值:
        适合传递给 :func:`sys.exit` 的整数退出码。

    异常:
        ValueError: 子命令参数违反生产配置约束时抛出。Argparse 自身的语法错误
        按标准行为转换为 ``SystemExit``。

    副作用:
        根据子命令向标准输出写入结果；当前命令不会写文件。
    """

    args = build_parser().parse_args(argv)
    if args.command == "system-info":
        return _run_system_info(args.cpu_percent, args.workers)

    # 子解析器由本模块集中注册，正常情况下不可能到达这里；保留显式失败可防止
    # 未来新增命令时忘记接线而静默返回成功。
    raise RuntimeError(f"未注册的命令处理器：{args.command}")
