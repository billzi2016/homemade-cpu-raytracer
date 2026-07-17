"""通过正式工作流生成并发布 README 所需真实图片。"""

from renderer.workflows import publish_readme_results


def main() -> int:
    """使用 Spec 默认参数写入 outputs 与 docs/images。"""

    report = publish_readme_results("outputs", "docs/images")
    print(report["published"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
