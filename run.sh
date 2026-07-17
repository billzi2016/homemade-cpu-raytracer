#!/usr/bin/env bash
# 意图：把简短 Shell 命令转交给唯一正式 Python CLI，不复制渲染或验证逻辑。
# 输入：无参数时加载 params/default.toml；也可传入方法名或正式 CLI 子命令。
# 输出：生产 CLI 的标准输出、退出码和正式结果文件。
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}src"

if [[ $# -eq 0 ]]; then
    exec python3 -m renderer preset --file params/default.toml
fi

command_name="$1"
shift

case "${command_name}" in
    rasterization|ray-casting|whitted|radiosity|path-tracing)
        if [[ $# -eq 0 ]]; then
            exec python3 -m renderer preset --file params/default.toml --method "${command_name}"
        fi
        exec python3 -m renderer render --method "${command_name}" "$@"
        ;;
    all|validate|readme|system-info|preset)
        exec python3 -m renderer "${command_name}" "$@"
        ;;
    *)
        echo "未知命令: ${command_name}" >&2
        exit 2
        ;;
esac
