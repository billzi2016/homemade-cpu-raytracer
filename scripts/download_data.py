"""按 data/manifest.json 下载可选资产并验证 SHA-256。

Cornell Box 由代码生成，不依赖本脚本。Manifest 可为空；一旦添加外部资产，每项
必须同时给出 URL、相对目标路径、许可证和 SHA-256，下载失败绝不写入伪造数据。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request


def download_manifest(manifest_path: Path, destination_root: Path) -> list[Path]:
    """下载并校验 manifest 中全部资产，返回最终文件路径列表。"""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("manifest.assets 必须是列表")
    completed: list[Path] = []
    for asset in assets:
        required = {"url", "path", "sha256", "license"}
        if not isinstance(asset, dict) or not required.issubset(asset):
            raise ValueError("每个资产必须包含 url/path/sha256/license")
        target = destination_root / str(asset["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(str(asset["url"]), timeout=60) as response:
            payload = response.read()
        digest = hashlib.sha256(payload).hexdigest()
        if digest.lower() != str(asset["sha256"]).lower():
            raise ValueError(f"资产 {asset['path']} 的 SHA-256 不匹配")
        target.write_bytes(payload)
        completed.append(target)
    return completed


def main() -> int:
    """读取项目默认清单并下载到被 Git 忽略的数据目录。"""

    files = download_manifest(Path("data/manifest.json"), Path("data/downloads"))
    print(f"已验证下载 {len(files)} 个可选资产；Cornell Box 无需下载。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
