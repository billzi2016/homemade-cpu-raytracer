# Homemade CPU Renderer

[English](README.md)

这是一个强调可维护性的纯 CPU 渲染项目：在统一 Cornell Box 中对比五种渲染方法。项目将数学和物理验证视为正式产物；一张图片仅仅“看起来合理”，不能证明实现正确。

## 五种渲染方法

| 方法 | 可见性模型 | 支持的光路 | 核心验证 |
| --- | --- | --- | --- |
| Rasterization（光栅化） | 三角形投影与 Z-Buffer | 局部直接光照 | 投影与深度顺序 |
| Ray Casting（光线投射） | 主射线与阴影射线 | 直接光照与硬阴影 | 解析射线交点 |
| Whitted Ray Tracing | 确定性递归射线 | 直接光、理想反射与理想折射 | 反射定律、Snell 定律与有限吞吐量 |
| Radiosity（辐射度） | Patch 间能量交换 | 漫反射全局光照与颜色晕染 | Form Factor 互易性与线性系统残差 |
| PBR Path Tracing | 渲染方程的 Monte Carlo 积分 | 混合直接与间接光路 | 能量守恒、白炉测试与 MSE 收敛 |

Rasterization 是唯一不使用光线追踪的 baseline。在数学模型允许公平对比的范围内，五种方法共享相同场景定义、相机、线性色彩管线、输出编码和 CPU 资源策略。

## 为什么使用 Cornell Box？

Cornell Box 的几何足够容易理解，同时能暴露真正重要的算法差异：

- 可见性与深度顺序；
- 直接光照与阴影；
- 理想镜面反射与介质折射；
- 漫反射互相照明以及红绿墙颜色晕染；
- 随每像素采样数（SPP）增加而产生的统计收敛。

标准场景通过代码程序化生成，保证核心工程离线可复现。可选参考资产单独下载，并记录来源、许可证和 SHA-256 校验值。

## 正确性优先于观感

项目直接验证生产实现，不使用 Mock 渲染器、硬编码结果图片、测试专用算法或另一套“快速验证”路径。

最终正式结果将保留：

- 五种方法各自的渲染图；
- 带明确标签的五方法对比图；
- Path Tracing 多档 SPP 结果；
- MSE 与标准误差收敛曲线；
- 白炉测试与能量守恒报告；
- Radiosity Form Factor 与求解器残差报告；
- CPU、Worker 数、内存、Seed 和耗时元数据。

验证通过的结果保存在 `outputs/` 并提交到仓库。README 图片从这些真实输出生成，而不是手工制作示意图。

## CPU 资源策略

渲染采用进程级并行。默认 Worker 数约为当前可见逻辑 CPU 数的 90%；多核机器至少为操作系统保留一个逻辑核心。

每个 Worker 会限制 BLAS、NumExpr、Numba 等数值后端的内部线程，避免多进程嵌套多线程造成过度订阅。这里的“90%”表示基于逻辑核心数量的容量策略，不承诺操作系统监控值在每一时刻都精确保持 90%。

## 安装

需要 Python 3.11 或更高版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

可选的 Embree 兼容 CPU 求交后端安装命令：

```bash
python3 -m pip install -e '.[dev,embree]'
```

## 当前可执行接口

共享工程骨架已经实现并通过测试。目前的生产 CLI 可以检查真实 CPU 分配策略：

```bash
python3 -m renderer system-info --cpu-percent 90
```

在一台具有 24 个逻辑 CPU 的主机上，输出示例为：

```json
{"cpu_percent": 90.0, "logical_cpus": 24, "workers": 21}
```

只有渲染命令完成生产实现并通过验证后，才会在这里加入相应命令和真实图片。

## 架构

```text
src/renderer/
├── core/          # 射线、颜色转换与公共数值契约
├── geometry/      # 网格适配、投影和求交后端
├── materials/     # 漫反射、镜面与介质材质契约
├── lights/        # 点光源与面光源
├── scenes/        # 共享 Cornell Box 与白炉场景
├── methods/       # 五种相互独立的渲染算法
├── parallel/      # Worker 策略、线程限制、Tile 与确定性 Seed
├── validation/    # 几何、能量、辐射度、白炉与收敛验证
└── output/        # PNG 编码、图表、拼图与运行元数据
```

架构遵循 SOLID 与 DRY，但不会为了形式上的统一，把数学含义不同的算法强行塞进一套误导性实现。共享场景、几何、颜色、资源、输出和验证规则各自只有一个事实来源；每种方法保留真正不同的渲染逻辑。

## 文档与代码质量

每个项目自有代码文件都以中文模块意图说明开头。函数、方法和类使用中文说明参数、返回值、异常、副作用、单位、坐标系和相关前置条件。复杂公式、数值容差、能量权重、随机采样与多进程边界具有就近中文解释。

项目约束和文件职责参见：

- [`specs/PRD.md`](specs/PRD.md)
- [`specs/PROJECT_TREE.md`](specs/PROJECT_TREE.md)

## 测试

使用以下命令运行生产契约测试：

```bash
PYTHONPATH=src python3 -m pytest -p no:cacheprovider tests
```

当前工程骨架测试覆盖配置校验、归一化只读射线、线性 RGB 到 sRGB 输出、Worker 分配、Tile 精确覆盖和确定性独立 Seed 派生。
