"""CLI、Shell 和文档生成共享的唯一正式工作流。

本模块组合生产渲染器、验证器和输出层，不重新实现任何算法。所有公开工作流都会
保存真实 PNG 与 JSON；README 发布只复制已经生成并验证的结果。
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import shutil
from typing import Any

import numpy as np

from renderer.config import RenderConfig, RenderMethod
from renderer.output import create_montage, save_convergence_chart, save_png, write_json
from renderer.parallel.executor import render_parallel
from renderer.scenes import create_cornell_box
from renderer.validation import mean_squared_error, run_white_furnace, validate_material_energy


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
) -> dict[str, Any]:
    """渲染一种方法并保存 PNG 与 JSON 元数据。

    返回可序列化报告，其中包含实际路径、耗时、Worker 和 Tile 数。所有参数直接
    进入生产 ``RenderConfig`` 与统一执行器，不存在演示参数替换。
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
    )
    result = render_parallel(config, samples_per_pixel=samples_per_pixel, max_depth=max_depth)
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
) -> dict[str, Any]:
    """依次运行五种正式方法并生成带标签对比拼图。"""

    reports = [
        render_method(method, output_root, width, height, samples_per_pixel, max_depth, cpu_percent, workers, seed)
        for method in RenderMethod
    ]
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
) -> dict[str, Any]:
    """用同一生产 Path Tracer 生成多 SPP 图、参考图和 MSE 曲线。"""

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
    reference = render_parallel(reference_config, samples_per_pixel=reference_spp, max_depth=8).image
    reference_path = root / "renders" / "path_tracing" / f"convergence_reference_{reference_spp}spp.png"
    save_png(reference, reference_path)
    errors: list[float] = []
    images: list[str] = []
    for level in levels:
        estimate = render_parallel(reference_config, samples_per_pixel=level, max_depth=8).image
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
    cpu_percent: float = 90.0,
    workers: int | None = None,
    seed: int = 20260716,
) -> dict[str, Any]:
    """生成全部正式结果并复制 README 所需的已验证图片。"""

    all_methods = render_all_methods(
        output_root, width, height, samples_per_pixel, 8, cpu_percent, workers, seed
    )
    convergence = render_convergence(
        output_root,
        width,
        height,
        (1, 4, 16),
        reference_spp,
        cpu_percent,
        workers,
        seed,
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
