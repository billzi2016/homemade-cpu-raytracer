"""正式渲染、验证与输出工作流的真实文件集成测试。"""

import json
from pathlib import Path

from renderer.config import RenderMethod
from renderer.workflows import render_method, validate_all


def test_render_method_writes_png_and_metadata(tmp_path: Path) -> None:
    """单方法工作流应通过生产执行器写入真实 PNG 与 JSON。"""

    report = render_method(
        RenderMethod.RASTERIZATION,
        tmp_path,
        width=12,
        height=12,
        workers=2,
    )
    assert Path(report["image"]).is_file()
    metadata = json.loads(Path(report["report"]).read_text(encoding="utf-8"))
    assert metadata["method"] == "rasterization"
    assert metadata["workers"] == 1


def test_validation_workflow_writes_passing_evidence(tmp_path: Path) -> None:
    """能量和白炉工作流应写入通过报告与真实图像。"""

    report = validate_all(tmp_path, furnace_width=8, furnace_height=8, furnace_spp=2, seed=3)
    assert report["passed"] is True
    assert Path(report["white_furnace"]["image"]).is_file()
