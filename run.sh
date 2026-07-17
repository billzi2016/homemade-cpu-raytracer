#!/usr/bin/env bash
# 意图：把简短 Shell 命令转交给唯一正式 Python CLI，不复制渲染或验证逻辑。
# 输入：第一个参数为 render/all/validate/readme/system-info，其余参数原样传递。
# 输出：生产 CLI 的标准输出、退出码和正式结果文件。
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}src"

if [[ $# -lt 1 ]]; then
    echo "用法: ./run.sh {rasterization|ray-casting|whitted|radiosity|path-tracing|all|validate|readme|system-info} [参数...]" >&2
    exit 2
fi

command_name="$1"
shift

case "${command_name}" in
    rasterization|ray-casting|whitted|radiosity|path-tracing)
        exec python3 -m renderer render --method "${command_name}" "$@"
        ;;
    all|validate|readme|system-info)
        exec python3 -m renderer "${command_name}" "$@"
        ;;
    *)
        echo "未知命令: ${command_name}" >&2
        exit 2
        ;;
esac
