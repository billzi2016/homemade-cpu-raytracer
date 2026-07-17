"""可复查运行元数据的确定性 JSON 写入。"""

import json
from pathlib import Path
from typing import Any


def write_json(data: dict[str, Any], path: str | Path) -> Path:
    """以 UTF-8、排序键和两空格缩进写入 JSON，并返回目标路径。"""

    destination = Path(path)
    if destination.suffix.lower() != ".json":
        raise ValueError("元数据输出必须使用 .json 扩展名")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination
