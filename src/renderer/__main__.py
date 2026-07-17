"""支持通过 ``python -m renderer`` 启动正式命令行入口。

本模块仅负责把 Python 模块执行协议转交给 :mod:`renderer.cli`，不复制参数解析
或业务逻辑，从而保证控制台脚本与模块启动方式始终走同一条生产路径。
"""

from renderer.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
