"""公共渲染配置的正式契约测试。

测试直接实例化生产配置并调用真实 Worker 计算，不替换系统函数、不使用 Mock。
显式传入逻辑核心数是公开依赖注入接口，用于验证同一生产公式的确定性边界。
"""

from pathlib import Path

import pytest

from renderer.config import RenderConfig, RenderMethod


def test_render_config_defaults_are_valid_and_resolve_workers() -> None:
    """默认配置应指向 Cornell Box，并按九成容量保留一个核心。"""

    config = RenderConfig(method=RenderMethod.PATH_TRACING)

    assert config.scene == "cornell-box"
    assert config.output_dir == Path("outputs")
    assert config.resolved_workers(logical_count=10) == 9


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scene", "  "),
        ("width", 0),
        ("height", -1),
        ("cpu_percent", 0.0),
        ("cpu_percent", 100.1),
        ("workers", 0),
        ("seed", -1),
        ("tile_width", 0),
    ],
)
def test_render_config_rejects_invalid_values(field: str, value: object) -> None:
    """所有跨渲染器共享的非法配置都应在模型边界被拒绝。"""

    values: dict[str, object] = {"method": RenderMethod.RASTERIZATION, field: value}
    with pytest.raises(ValueError):
        RenderConfig(**values)  # type: ignore[arg-type]


def test_render_method_contains_exactly_the_five_spec_methods() -> None:
    """方法枚举必须与 Spec 的五条路线一一对应。"""

    assert {method.value for method in RenderMethod} == {
        "rasterization",
        "ray-casting",
        "whitted",
        "radiosity",
        "path-tracing",
    }
