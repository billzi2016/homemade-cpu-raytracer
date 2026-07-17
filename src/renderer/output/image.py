"""线性 HDR RGB 到 PNG 的唯一正式写入路径。"""

from pathlib import Path

import numpy as np
from PIL import Image

from renderer.core.color import encode_rgb8


def save_png(linear_rgb: object, path: str | Path) -> Path:
    """色调映射、sRGB 编码并原子式保存 RGB PNG。

    参数:
        linear_rgb: 形状 ``(H,W,3)`` 的非负有限线性 HDR 图像。
        path: 目标 PNG 路径；父目录不存在时创建。
    返回值:
        规范化 :class:`Path`。
    异常:
        ValueError: 图像维度或扩展名非法时抛出；I/O 错误原样传播。
    副作用:
        创建父目录并写入目标文件。
    """

    destination = Path(path)
    if destination.suffix.lower() != ".png":
        raise ValueError("正式图像输出必须使用 .png 扩展名")
    array = np.asarray(linear_rgb)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError("图像必须是 (H, W, 3) RGB 数组")
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(encode_rgb8(array), mode="RGB").save(destination)
    return destination
