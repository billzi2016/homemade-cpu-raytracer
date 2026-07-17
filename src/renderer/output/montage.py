"""使用 Pillow 生成带文字标签的真实渲染对比图。"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


_LABEL_FONT_SIZE = 28
_LABEL_HEIGHT = 52


def _load_label_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """加载 Pillow 随附的跨平台粗体字体，缺失时回退到可缩放默认字体。

    DejaVu Sans Bold 随常见 Pillow 发行包提供，能让 1536 像素宽的 GitHub 对比图
    标签保持清晰。回退路径仍显式请求 28px，避免旧版固定小字体重新出现。
    """

    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", _LABEL_FONT_SIZE)
    except OSError:
        return ImageFont.load_default(size=_LABEL_FONT_SIZE)


def create_montage(images: list[tuple[str, str | Path]], destination: str | Path, columns: int = 3) -> Path:
    """读取 PNG 列表并创建等尺寸标签网格；不接受空列表或尺寸不一致图片。"""

    if not images or columns <= 0:
        raise ValueError("images 不能为空且 columns 必须为正")
    loaded = [(label, Image.open(path).convert("RGB")) for label, path in images]
    width, height = loaded[0][1].size
    if any(image.size != (width, height) for _, image in loaded):
        raise ValueError("拼图输入尺寸必须一致")
    rows = (len(loaded) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * width, rows * (height + _LABEL_HEIGHT)), "white")
    draw = ImageDraw.Draw(canvas)
    font = _load_label_font()
    for index, (label, image) in enumerate(loaded):
        x = (index % columns) * width
        y = (index // columns) * (height + _LABEL_HEIGHT)
        canvas.paste(image, (x, y + _LABEL_HEIGHT))
        draw.text((x + 12, y + 9), label, fill="black", font=font)
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    for _, image in loaded:
        image.close()
    return output
