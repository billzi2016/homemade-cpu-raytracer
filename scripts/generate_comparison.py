"""通过正式工作流生成五种方法对比图，不实现任何渲染算法。"""

from renderer.workflows import render_all_methods


def main() -> int:
    """使用 Spec 默认参数生成正式对比结果。"""

    report = render_all_methods("outputs")
    print(report["comparison"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
