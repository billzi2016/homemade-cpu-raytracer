"""使用 Pillow 生成带文字标签的真实渲染对比图。"""

from pathlib import Path
from PIL import Image, ImageDraw


def create_montage(images: list[tuple[str, str | Path]], destination: str | Path, columns: int = 3) -> Path:
    """读取 PNG 列表并创建等尺寸标签网格；不接受空列表或尺寸不一致图片。"""

    if not images or columns <= 0:
        raise ValueError("images 不能为空且 columns 必须为正")
    loaded = [(label, Image.open(path).convert("RGB")) for label, path in images]
    width, height = loaded[0][1].size
    if any(image.size != (width, height) for _, image in loaded):
        raise ValueError("拼图输入尺寸必须一致")
    label_height = 28
    rows = (len(loaded) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * width, rows * (height + label_height)), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (label, image) in enumerate(loaded):
        x = (index % columns) * width
        y = (index // columns) * (height + label_height)
        canvas.paste(image, (x, y + label_height))
        draw.text((x + 8, y + 7), label, fill="black")
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    for _, image in loaded:
        image.close()
    return output
