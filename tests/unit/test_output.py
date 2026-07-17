"""正式 PNG、JSON、拼图和收敛图输出测试。"""

import json
from pathlib import Path
import numpy as np
from PIL import Image

from renderer.output import create_montage, save_convergence_chart, save_png, write_json


def test_output_pipeline_writes_real_artifacts(tmp_path: Path) -> None:
    """公共输出层应生成可读取 PNG、JSON、拼图和非空曲线。"""

    image = np.full((8, 8, 3), 0.5, dtype=np.float64)
    first = save_png(image, tmp_path / "first.png")
    second = save_png(image * 2.0, tmp_path / "second.png")
    report = write_json({"workers": 2, "passed": True}, tmp_path / "report.json")
    montage = create_montage([("First", first), ("Second", second)], tmp_path / "montage.png", columns=2)
    chart = save_convergence_chart([1, 4, 16], [0.1, 0.025, 0.00625], tmp_path / "chart.png")

    assert Image.open(first).size == (8, 8)
    assert Image.open(montage).size == (16, 36)
    assert json.loads(report.read_text(encoding="utf-8"))["passed"] is True
    assert chart.stat().st_size > 0
