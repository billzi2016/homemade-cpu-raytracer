"""使用 Matplotlib 生成 Path Tracing 收敛曲线。"""

from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def save_convergence_chart(samples: list[int], mse: list[float], destination: str | Path) -> Path:
    """以双对数坐标保存 SPP/MSE 曲线；输入必须同长、正数且至少两点。"""

    if len(samples) != len(mse) or len(samples) < 2:
        raise ValueError("samples 与 mse 必须同长且至少包含两点")
    if any(value <= 0 for value in samples) or any(value <= 0.0 for value in mse):
        raise ValueError("SPP 与 MSE 必须全部为正")
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(7.2, 4.6), constrained_layout=True)
    axis.loglog(samples, mse, marker="o", linewidth=2, label="Measured MSE")
    reference = [mse[0] * samples[0] / sample for sample in samples]
    axis.loglog(samples, reference, linestyle="--", label="O(1/N) reference")
    axis.set_xlabel("Samples per pixel (SPP)")
    axis.set_ylabel("Mean squared error")
    axis.set_title("Path Tracing Convergence")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend()
    figure.savefig(output, dpi=160)
    plt.close(figure)
    return output
