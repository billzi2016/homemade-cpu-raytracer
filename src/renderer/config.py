"""五种渲染方法共享的不可变配置模型。

本模块负责统一校验图像尺寸、场景名、随机种子、Tile 尺寸和 CPU 资源参数，
防止各渲染器复制并逐渐分叉出不同配置规则。它不读取环境变量、不创建输出目录，
也不启动 Worker；这些副作用由命令层和并行层负责。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from pathlib import Path

from renderer.parallel.resources import compute_worker_count


class RenderMethod(StrEnum):
    """Spec 规定的五种渲染方法标识。

    枚举值直接用于 CLI、输出目录和 JSON 元数据，因而必须保持稳定。新增方法时
    应先更新 Spec，再在此处扩展，不能由各渲染器私自定义字符串别名。
    """

    RASTERIZATION = "rasterization"
    RAY_CASTING = "ray-casting"
    WHITTED = "whitted"
    RADIOSITY = "radiosity"
    PATH_TRACING = "path-tracing"


@dataclass(frozen=True, slots=True)
class RenderQuality:
    """描述非 Path Tracing 方法的正式质量等级。

    参数:
        deterministic_samples_per_pixel: Rasterization、Ray Casting 与 Whitted 的
            规则网格超采样数，必须是正整数完全平方数。
        sphere_subdivisions: 混合 Cornell Box 的 Icosphere 细分级数。
        radiosity_subdivision_levels: 每个原始三角形递归四分为 Patch 的级数。
    异常:
        ValueError: 任一字段不满足边界或超采样数不是完全平方数时抛出。
    副作用:
        无；配置不可变且可安全序列化到多进程 Worker。
    """

    deterministic_samples_per_pixel: int = 1
    sphere_subdivisions: int = 2
    radiosity_subdivision_levels: int = 2

    def __post_init__(self) -> None:
        """验证质量参数，防止昂贵运行静默采用无法解释的设置。"""

        values = (
            self.deterministic_samples_per_pixel,
            self.sphere_subdivisions,
            self.radiosity_subdivision_levels,
        )
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            raise ValueError("渲染质量参数必须是整数")
        if self.deterministic_samples_per_pixel <= 0:
            raise ValueError("deterministic_samples_per_pixel 必须为正整数")
        grid_size = math.isqrt(self.deterministic_samples_per_pixel)
        if grid_size * grid_size != self.deterministic_samples_per_pixel:
            raise ValueError("deterministic_samples_per_pixel 必须是完全平方数")
        if not 1 <= self.sphere_subdivisions <= 5:
            raise ValueError("sphere_subdivisions 必须位于 [1, 5]")
        if not 0 <= self.radiosity_subdivision_levels <= 3:
            raise ValueError("radiosity_subdivision_levels 必须位于 [0, 3]")


@dataclass(frozen=True, slots=True)
class RenderConfig:
    """描述一次正式渲染的公共配置。

    参数:
        method: 需要执行的渲染方法。
        scene: 场景注册名，不能为空。
        width: 输出宽度，单位为像素，必须为正数。
        height: 输出高度，单位为像素，必须为正数。
        cpu_percent: 未显式指定 Worker 时允许使用的逻辑 CPU 百分比。
        workers: 显式进程数；为 ``None`` 时按 ``cpu_percent`` 计算。
        seed: 非负随机种子，用于派生每个 Tile 的独立随机流。
        output_dir: 生成物根目录；模型只保存路径，不主动创建目录。
        tile_width: Tile 宽度，单位为像素，必须为正数。
        tile_height: Tile 高度，单位为像素，必须为正数。
        quality: 非 Path Tracing 方法共享的不可变质量配置。

    异常:
        ValueError: 任意尺寸、资源比例、Worker 数、场景名或 Seed 非法时抛出。

    副作用:
        无。实例不可变，可安全传递给调度器和元数据输出模块。
    """

    method: RenderMethod
    scene: str = "cornell-box"
    width: int = 512
    height: int = 512
    cpu_percent: float = 90.0
    workers: int | None = None
    seed: int = 20260716
    output_dir: Path = Path("outputs")
    tile_width: int = 16
    tile_height: int = 16
    quality: RenderQuality = field(default_factory=RenderQuality)

    def __post_init__(self) -> None:
        """校验配置自身能够独立判断的结构约束。

        返回值:
            无。

        异常:
            ValueError: 字段不满足类文档描述的约束时抛出。

        副作用:
            无；冻结数据类只进行读取和校验。
        """

        if not isinstance(self.method, RenderMethod):
            raise ValueError("method 必须是 RenderMethod 枚举值")
        if not self.scene.strip():
            raise ValueError("scene 不能为空")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("图像宽高必须为正整数")
        if self.tile_width <= 0 or self.tile_height <= 0:
            raise ValueError("Tile 宽高必须为正整数")
        if not 0.0 < self.cpu_percent <= 100.0:
            raise ValueError("cpu_percent 必须位于 (0, 100] 区间")
        if self.workers is not None and self.workers <= 0:
            raise ValueError("workers 必须为正整数或 None")
        if self.seed < 0:
            raise ValueError("seed 必须为非负整数")
        if not isinstance(self.quality, RenderQuality):
            raise ValueError("quality 必须是 RenderQuality")

    def resolved_workers(self, logical_count: int | None = None) -> int:
        """根据公共资源策略解析最终 Worker 数。

        参数:
            logical_count: 用于计算的逻辑核心数。为 ``None`` 时探测当前机器；
                显式传值可用于调度器已知资源或纯函数测试，不代表 Mock。

        返回值:
            至少为 1 且不超过逻辑核心数的进程数量。

        异常:
            ValueError: ``logical_count`` 或配置中的资源参数非法时抛出。

        副作用:
            仅在 ``logical_count`` 为 ``None`` 时读取本机 CPU 信息。
        """

        return compute_worker_count(
            cpu_percent=self.cpu_percent,
            explicit_workers=self.workers,
            logical_count=logical_count,
        )
