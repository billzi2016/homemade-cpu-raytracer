"""默认 TOML 高清参数的正式解析与严格字段测试。"""

from pathlib import Path
import pytest

from renderer.workflows import load_readme_preset
from renderer.cli import build_parser


def test_default_preset_uses_requested_hd_resolution() -> None:
    """仓库默认参数必须加载 512 平方、128 Path SPP 与加强后的四方法质量。"""

    preset = load_readme_preset(Path("params/default.toml"))
    assert preset["width"] == 512
    assert preset["height"] == 512
    assert preset["samples_per_pixel"] == 128
    assert preset["reference_spp"] == 1024
    assert preset["deterministic_samples_per_pixel"] == 9
    assert preset["sphere_subdivisions"] == 3
    assert preset["radiosity_subdivision_levels"] == 3
    assert preset["tile_size"] == 32
    assert preset["cpu_percent"] == 90.0


def test_preset_rejects_unknown_or_missing_fields(tmp_path: Path) -> None:
    """未知或缺失字段必须失败，不能静默采用另一套默认值。"""

    invalid = tmp_path / "invalid.toml"
    invalid.write_text("[readme]\nwidth = 1024\nunknown = true\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_readme_preset(invalid)


def test_preset_cli_accepts_one_production_method() -> None:
    """Preset 子命令应能选择单个方法，同时仍使用同一默认 TOML。"""

    args = build_parser().parse_args(["preset", "--method", "whitted"])
    assert args.command == "preset"
    assert args.method == "whitted"
    assert args.file == "params/default.toml"
