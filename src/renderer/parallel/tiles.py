"""二维图像的确定性 Tile 划分。

Tile 是多进程渲染任务的最小空间单元。划分按从上到下、从左到右的固定顺序
生成半开区间，保证无重叠、无遗漏，并使 Tile 索引能够稳定派生随机流。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tile:
    """图像中的矩形半开区域 ``[x0, x1) × [y0, y1)``。

    参数:
        index: 按扫描线顺序生成的非负稳定编号。
        x0: 左边界像素索引，包含在 Tile 内。
        y0: 上边界像素索引，包含在 Tile 内。
        x1: 右边界像素索引，不包含在 Tile 内。
        y1: 下边界像素索引，不包含在 Tile 内。

    异常:
        ValueError: 索引为负、起点为负或区域为空/反向时抛出。

    副作用:
        无；实例不可变，可安全序列化给子进程。
    """

    index: int
    x0: int
    y0: int
    x1: int
    y1: int

    def __post_init__(self) -> None:
        """校验半开矩形边界。

        返回值:
            无。

        异常:
            ValueError: 字段不构成合法非空图像区域时抛出。

        副作用:
            无。
        """

        values = (self.index, self.x0, self.y0, self.x1, self.y1)
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            raise ValueError("Tile 的索引和边界必须是整数")
        if self.index < 0 or self.x0 < 0 or self.y0 < 0:
            raise ValueError("Tile 索引和起始边界不能为负")
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("Tile 必须是非空的正向半开区域")

    @property
    def width(self) -> int:
        """返回 Tile 宽度，单位为像素，无副作用。"""

        return self.x1 - self.x0

    @property
    def height(self) -> int:
        """返回 Tile 高度，单位为像素，无副作用。"""

        return self.y1 - self.y0

    @property
    def pixel_count(self) -> int:
        """返回 Tile 覆盖的像素数量，无副作用。"""

        return self.width * self.height


def split_into_tiles(
    width: int,
    height: int,
    tile_width: int = 32,
    tile_height: int = 32,
) -> tuple[Tile, ...]:
    """将完整图像确定性划分为无重叠 Tile。

    参数:
        width: 图像宽度，单位为像素。
        height: 图像高度，单位为像素。
        tile_width: 常规 Tile 宽度；最右侧 Tile 可更窄。
        tile_height: 常规 Tile 高度；最下侧 Tile 可更矮。

    返回值:
        按 ``y`` 后 ``x`` 扫描线顺序排列的不可变 Tile 元组，其并集恰好覆盖图像。

    异常:
        ValueError: 任意尺寸不是正整数时抛出。

    副作用:
        无。
    """

    dimensions = {
        "width": width,
        "height": height,
        "tile_width": tile_width,
        "tile_height": tile_height,
    }
    for name, value in dimensions.items():
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} 必须是正整数")

    tiles: list[Tile] = []
    index = 0
    for y0 in range(0, height, tile_height):
        y1 = min(y0 + tile_height, height)
        for x0 in range(0, width, tile_width):
            x1 = min(x0 + tile_width, width)
            tiles.append(Tile(index=index, x0=x0, y0=y0, x1=x1, y1=y1))
            index += 1
    return tuple(tiles)
