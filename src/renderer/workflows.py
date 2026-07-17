"""CLI、Shell 和文档生成共享的唯一正式工作流。

本模块组合生产渲染器、验证器和输出层，不重新实现任何算法。所有公开工作流都会
保存真实 PNG 与 JSON；README 发布只复制已经生成并验证的结果。
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import shutil
import tomllib
from typing import Any

import numpy as np
from tqdm.auto import tqdm

from renderer.config import RenderConfig, RenderMethod, RenderQuality
from renderer.output import create_montage, save_convergence_chart, save_png, write_json
from renderer.parallel.executor import render_parallel
from renderer.scenes import create_cornell_box
from renderer.validation import mean_squared_error, run_white_furnace, validate_material_energy


_PRESET_KEYS = {
    "width",
    "height",
    "samples_per_pixel",
    "reference_spp",
    "convergence_size",
    "deterministic_samples_per_pixel",
    "sphere_subdivisions",
    "radiosity_subdivision_levels",
    "tile_size",
    "cpu_percent",
    "seed",
    "output_root",
    "docs_root",
}


def load_readme_preset(path: str | Path) -> dict[str, Any]:
    """读取并严格校验默认 README TOML 参数。

    未知字段、缺失字段、非正尺寸/SPP 或非法 CPU 百分比都会抛出 ``ValueError``，
    防止拼写错误被静默忽略后运行昂贵的错误渲染。本函数只读取文件，不生成结果。
    """

    source = Path(path)
    with source.open("rb") as handle:
        document = tomllib.load(handle)
    readme = document.get("readme")
    if not isinstance(readme, dict):
        raise ValueError("参数文件必须包含 [readme] 表")
    keys = set(readme)
    if keys != _PRESET_KEYS:
        missing = sorted(_PRESET_KEYS - keys)
        unknown = sorted(keys - _PRESET_KEYS)
        raise ValueError(f"参数字段不一致；缺失={missing}，未知={unknown}")
    positive_integer_keys = (
        "width",
        "height",
        "samples_per_pixel",
        "reference_spp",
        "convergence_size",
        "deterministic_samples_per_pixel",
        "sphere_subdivisions",
        "radiosity_subdivision_levels",
        "tile_size",
    )
    if any(not isinstance(readme[key], int) or isinstance(readme[key], bool) or readme[key] <= 0 for key in positive_integer_keys):
        raise ValueError("尺寸和 SPP 参数必须是正整数")
    if readme["reference_spp"] <= 16:
        raise ValueError("reference_spp 必须大于最高收敛档位 16")
    if not isinstance(readme["seed"], int) or isinstance(readme["seed"], bool) or readme["seed"] < 0:
        raise ValueError("seed 必须是非负整数")
    cpu_percent = float(readme["cpu_percent"])
    if not 0.0 < cpu_percent <= 100.0:
        raise ValueError("cpu_percent 必须位于 (0, 100]")
    if not isinstance(readme["output_root"], str) or not isinstance(readme["docs_root"], str):
        raise ValueError("输出目录参数必须是字符串")
    return dict(readme)


def _quality_from_preset(parameters: dict[str, Any]) -> RenderQuality:
    """从已严格校验的 TOML 字典构造唯一生产质量模型。"""

    return RenderQuality(
        deterministic_samples_per_pixel=parameters["deterministic_samples_per_pixel"],
        sphere_subdivisions=parameters["sphere_subdivisions"],
        radiosity_subdivision_levels=parameters["radiosity_subdivision_levels"],
    )


def render_method_from_preset(path: str | Path, method: RenderMethod) -> dict[str, Any]:
    """加载默认 TOML 并只运行指定方法，参数与完整发布流程完全一致。

    本函数复用 :func:`render_method`，不维护第二套渲染逻辑。Path Tracing 读取
    ``samples_per_pixel``；其他确定性方法读取独立质量配置。
    """

    parameters = load_readme_preset(path)
    return render_method(
        method=method,
        output_root=parameters["output_root"],
        width=parameters["width"],
        height=parameters["height"],
        samples_per_pixel=parameters["samples_per_pixel"],
        max_depth=8,
        cpu_percent=float(parameters["cpu_percent"]),
        seed=parameters["seed"],
        show_progress=True,
        quality=_quality_from_preset(parameters),
        tile_size=parameters["tile_size"],
    )


def publish_readme_from_preset(path: str | Path) -> dict[str, Any]:
    """加载 TOML 后调用唯一正式 README 生产工作流。"""

    parameters = load_readme_preset(path)
    return publish_readme_results(
        parameters["output_root"],
        parameters["docs_root"],
        parameters["width"],
        parameters["height"],
        parameters["samples_per_pixel"],
        parameters["reference_spp"],
        parameters["convergence_size"],
        float(parameters["cpu_percent"]),
        None,
        parameters["seed"],
        True,
        _quality_from_preset(parameters),
        parameters["tile_size"],
    )


def default_scene_for_method(method: RenderMethod) -> str:
    """返回方法的正式默认场景；Whitted 使用镜面/玻璃变体，其余使用标准盒。"""

    return "cornell-box-mixed" if method == RenderMethod.WHITTED else "cornell-box"


def render_method(
    method: RenderMethod,
    output_root: str | Path,
    width: int = 128,
    height: int = 128,
    samples_per_pixel: int = 32,
    max_depth: int = 8,
    cpu_percent: float = 90.0,
    workers: int | None = None,
    seed: int = 20260716,
    scene_name: str | None = None,
    show_progress: bool = False,
    progress_position: int = 0,
    quality: RenderQuality | None = None,
    tile_size: int = 16,
) -> dict[str, Any]:
    """渲染一种方法并保存 PNG 与 JSON 元数据。

    ``show_progress`` 与 ``progress_position`` 只控制 stderr 展示，不改变计算结果。
    返回的可序列化报告包含实际路径、耗时、Worker 和 Tile 数。所有渲染参数直接
    进入生产 ``RenderConfig`` 与统一执行器，不存在演示参数替换或第二套逻辑。
    """

    root = Path(output_root)
    scene = scene_name or default_scene_for_method(method)
    config = RenderConfig(
        method=method,
        scene=scene,
        width=width,
        height=height,
        cpu_percent=cpu_percent,
        workers=workers,
        seed=seed,
        output_dir=root,
        quality=quality or RenderQuality(),
        tile_width=tile_size,
        tile_height=tile_size,
    )
    result = render_parallel(
        config,
        samples_per_pixel=samples_per_pixel,
        max_depth=max_depth,
        show_progress=show_progress,
        progress_position=progress_position,
    )
    image_path = root / "renders" / method.value / f"{scene}_{width}x{height}.png"
    report_path = root / "reports" / f"{method.value}.json"
    save_png(result.image, image_path)
    report: dict[str, Any] = {
        "method": method.value,
        "scene": scene,
        "width": width,
        "height": height,
        "samples_per_pixel": samples_per_pixel if method == RenderMethod.PATH_TRACING else None,
        "max_depth": max_depth if method in (RenderMethod.WHITTED, RenderMethod.PATH_TRACING) else None,
        "seed": seed,
        "cpu_percent": cpu_percent,
        "workers": result.workers,
        "tiles": result.tiles,
        "elapsed_seconds": result.elapsed_seconds,
        "image": str(image_path),
        "diagnostics": result.diagnostics,
        "quality": asdict(config.quality),
    }
    write_json(report, report_path)
    report["report"] = str(report_path)
    return report


def render_all_methods(
    output_root: str | Path,
    width: int = 128,
    height: int = 128,
    samples_per_pixel: int = 32,
    max_depth: int = 8,
    cpu_percent: float = 90.0,
    workers: int | None = None,
    seed: int = 20260716,
    show_progress: bool = False,
    quality: RenderQuality | None = None,
    tile_size: int = 16,
) -> dict[str, Any]:
    """依次运行五种正式方法并生成带标签对比拼图。

    启用 ``show_progress`` 时，第 0 行显示五方法总进度，第 1 行显示当前方法的
    Tile 或 Patch 进度；每种方法成功写出图片与报告后才增加总进度。
    """

    reports: list[dict[str, Any]] = []
    with tqdm(
        total=len(RenderMethod),
        desc="五种方法总进度",
        unit="method",
        position=0,
        leave=True,
        disable=not show_progress,
        dynamic_ncols=True,
    ) as overall:
        for method in RenderMethod:
            reports.append(
                render_method(
                    method,
                    output_root,
                    width,
                    height,
                    samples_per_pixel,
                    max_depth,
                    cpu_percent,
                    workers,
                    seed,
                    None,
                    show_progress,
                    1,
                    quality,
                    tile_size,
                )
            )
            overall.update(1)
    montage_path = Path(output_root) / "comparisons" / "five_methods.png"
    create_montage([(report["method"], report["image"]) for report in reports], montage_path, columns=3)
    summary = {"methods": reports, "comparison": str(montage_path)}
    write_json(summary, Path(output_root) / "reports" / "all_methods.json")
    return summary


def render_convergence(
    output_root: str | Path,
    width: int,
    height: int,
    levels: tuple[int, ...] = (1, 4, 16),
    reference_spp: int = 64,
    cpu_percent: float = 90.0,
    workers: int | None = None,
    seed: int = 20260716,
    show_progress: bool = False,
) -> dict[str, Any]:
    """用同一生产 Path Tracer 生成多 SPP 图、参考图和 MSE 曲线。

    ``show_progress`` 会为参考图和每个 SPP 档位显示基于完成 Tile 的 ETA，不改变
    固定 Seed 或任何统计计算。
    """

    if not levels or any(level <= 0 for level in levels) or reference_spp <= max(levels):
        raise ValueError("SPP levels 必须为正且 reference_spp 必须更大")
    root = Path(output_root)
    reference_config = RenderConfig(
        RenderMethod.PATH_TRACING,
        width=width,
        height=height,
        cpu_percent=cpu_percent,
        workers=workers,
        seed=seed,
    )
    reference = render_parallel(
        reference_config,
        samples_per_pixel=reference_spp,
        max_depth=8,
        show_progress=show_progress,
    ).image
    reference_path = root / "renders" / "path_tracing" / f"convergence_reference_{reference_spp}spp.png"
    save_png(reference, reference_path)
    errors: list[float] = []
    images: list[str] = []
    for level in levels:
        estimate = render_parallel(
            reference_config,
            samples_per_pixel=level,
            max_depth=8,
            show_progress=show_progress,
        ).image
        path = root / "renders" / "path_tracing" / f"convergence_{level}spp.png"
        save_png(estimate, path)
        images.append(str(path))
        errors.append(mean_squared_error(estimate, reference))
    chart = root / "charts" / "path_tracing_convergence.png"
    save_convergence_chart(list(levels), errors, chart)
    report = {
        "levels": list(levels),
        "reference_spp": reference_spp,
        "mse": errors,
        "images": images,
        "reference_image": str(reference_path),
        "chart": str(chart),
    }
    write_json(report, root / "reports" / "convergence.json")
    return report


def validate_all(
    output_root: str | Path,
    furnace_width: int = 24,
    furnace_height: int = 24,
    furnace_spp: int = 8,
    seed: int = 20260716,
) -> dict[str, Any]:
    """运行材质能量与正式白炉测试，并保存图片和 JSON 证据。"""

    root = Path(output_root)
    material_report = validate_material_energy(create_cornell_box(mixed_materials=True).materials)
    furnace = run_white_furnace(furnace_width, furnace_height, furnace_spp, seed=seed)
    furnace_path = root / "renders" / "white_furnace" / "white_furnace.png"
    save_png(furnace.image, furnace_path)
    report = {
        "passed": bool(material_report["passed"] and furnace.passed),
        "material_energy": material_report,
        "white_furnace": {
            "passed": furnace.passed,
            "max_absolute_error": furnace.max_absolute_error,
            "image": str(furnace_path),
            "samples_per_pixel": furnace_spp,
        },
    }
    write_json(report, root / "reports" / "validation.json")
    return report


def publish_readme_results(
    output_root: str | Path,
    docs_root: str | Path,
    width: int = 128,
    height: int = 128,
    samples_per_pixel: int = 32,
    reference_spp: int = 64,
    convergence_size: int = 128,
    cpu_percent: float = 90.0,
    workers: int | None = None,
    seed: int = 20260716,
    show_progress: bool = True,
    quality: RenderQuality | None = None,
    tile_size: int = 16,
) -> dict[str, Any]:
    """生成全部正式结果并复制 README 所需的已验证图片。"""

    all_methods = render_all_methods(
        output_root,
        width,
        height,
        samples_per_pixel,
        8,
        cpu_percent,
        workers,
        seed,
        show_progress,
        quality,
        tile_size,
    )
    convergence = render_convergence(
        output_root,
        convergence_size,
        convergence_size,
        (1, 4, 16),
        reference_spp,
        cpu_percent,
        workers,
        seed,
        show_progress,
    )
    validation = validate_all(output_root, 32, 32, 8, seed)
    docs = Path(docs_root)
    docs.mkdir(parents=True, exist_ok=True)
    published = {
        "five_methods": docs / "five_methods.png",
        "convergence": docs / "convergence.png",
        "white_furnace": docs / "white_furnace.png",
    }
    shutil.copy2(all_methods["comparison"], published["five_methods"])
    shutil.copy2(convergence["chart"], published["convergence"])
    shutil.copy2(validation["white_furnace"]["image"], published["white_furnace"])
    return {
        "all_methods": all_methods,
        "convergence": convergence,
        "validation": validation,
        "published": {name: str(path) for name, path in published.items()},
    }
