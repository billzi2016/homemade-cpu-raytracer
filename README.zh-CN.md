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

## 历史、效率与应用场景

下表介绍四种确定性方法。速度描述来自当前实现的任务规模和算法复杂度，不虚构尚未生成的跑分；每次正式运行都会把真实耗时、Worker 数、Tile 数和质量参数写入 `outputs/reports/*.json`，该报告才是实测性能的事实来源。

| 方法 | 历史节点 | 本项目中的速度与 CPU 效率 | 画面效果与限制 | 典型应用场景 |
| --- | --- | --- | --- | --- |
| Rasterization（光栅化） | 扫描转换在 1960 年代逐步形成；Edwin Catmull 的 [1974 年博士论文](https://cir.nii.ac.jp/crid/1971149384832865339)是早期 Z-Buffer 曲面显示的代表文献。 | 通常最快。主要成本是三角形覆盖和可见像素处理，独立 Tile 很适合多进程扩展。默认 3×3 抗锯齿会计算 9 个确定性子像素，但不会生成递归射线。 | 几何轮廓清晰，Gouraud 直接光梯度连续，深度顺序准确；没有光追反射、折射、间接光和物理阴影。 | 实时引擎、CAD 视口、游戏、界面预览，以及现代 GPU 管线的可见性阶段。 |
| Ray Casting（光线投射） | Arthur Appel 于 1968 年发表 [“Some Techniques for Shading Machine Renderings of Solids”](https://research.ibm.com/publications/some-techniques-for-shading-machine-renderings-of-solids)。 | 较快到中等。每个子像素发射一条主射线，并执行有限距离阴影求交。像素和 Tile 相互独立，多进程效率较好；成本随像素、样本、光源和求交三角形数增长。 | 主可见性精确，具有直接 Lambert 光和硬阴影。因为算法有意禁止间接弹跳，照不到的面保持黑色。 | 拾取与可见性查询、体渲染变体、简单离线预览、阴影测试和加速结构基线。 |
| Whitted Ray Tracing | Turner Whitted 在 SIGGRAPH [1979](https://doi.org/10.1145/800249.807419) 提出递归反射/折射，扩展版于 [1980](https://doi.org/10.1145/358876.358882) 发表于 CACM。 | 中等到较慢。Tile 可以良好并行，但镜面和介质命中会递归产生更多射线；耗时强烈依赖递归深度、反射物体、抗锯齿和求交成本。三级平滑球体提高几何质量，但不改变光路模型。 | 能得到清晰的理想镜面、玻璃折射、Fresnel 边缘、直接光和硬阴影；无法表现粗糙高光或漫反射间接颜色晕染。 | 理想玻璃/镜面产品展示、光学演示、经典离线渲染、图形学教学和确定性参考场景。 |
| Radiosity（辐射度） | Cindy Goral、Kenneth Torrance、Donald Greenberg 与 Bennett Battaile 在 [SIGGRAPH 1984](https://bowers.cornell.edu/cornell-box) 将该方法引入图形学，并产生最初的 Cornell Box 结果。 | 预计算较重：Patch 两两耦合近似二次复杂度，当前稠密线性求解最坏可接近三次复杂度，而且它是全局求解，不能像 Tile 那样拆开。求解后光照与视点无关，可供多个相机重复使用。 | 擅长稳定的漫反射全局光照、柔和能量传递和红绿颜色晕染。三级 Patch 与材质安全顶点插值会抑制明显三角色块；不能处理镜面和玻璃。 | 建筑照明、漫反射室内场景、静态 Lightmap 烘焙、可视化，以及表面能量交换验证。 |

Path Tracing 是第五种随机方法：速度更慢，但能覆盖最广的光路。它单独使用 Monte Carlo SPP 控制质量，上述确定性 3×3 设置不会乘到 Path Tracing 的路径数量上。

### 512×512 正式运行实测

以下数据直接来自本次提交保留的 JSON 报告，不是估算值。四种图像空间方法使用 21 个 Worker 进程；Radiosity 按模型要求由单进程完成全局求解；Path Tracing 使用 128 SPP。五张主图合计耗时 1,045.96 秒，约 17 分 26 秒，不包含收敛实验和白炉验证时间。

| 方法 | 实测耗时 | 相对 Rasterization |
| --- | ---: | ---: |
| Rasterization | 2.74 秒 | 1.0× |
| Ray Casting | 11.15 秒 | 4.1× |
| Whitted Ray Tracing | 253.61 秒 | 92.5× |
| Radiosity | 22.51 秒 | 8.2× |
| Path Tracing | 755.95 秒 | 275.9× |

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

终端显示两层 tqdm 进度：五种方法的总进度，以及当前方法已完成的 Tile 或 Radiosity Patch。tqdm 默认同时显示已用时间、处理速度和 ETA。

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

## 运行

默认参数为 512×512，主 Path Tracing 使用 128 SPP，较小的收敛参考图使用 1024 SPP，多进程 Tile 为 32×32，并使用约 90% 逻辑 CPU。其他方法使用 3×3 确定性抗锯齿、三级细分且采用平滑法线的 Whitted 球体，以及三级 Patch 细分和材质安全顶点插值的 Radiosity；这些质量参数不会增加 Path Tracing 的样本数。生成全部 README 正式结果只需要一个命令：

```bash
./run.sh
```

该命令依次执行五种生产渲染器、收敛实验、能量验证、白炉测试、对比图生成和 README 图片发布。参数唯一来源是 [`params/default.toml`](params/default.toml)。

使用同一套默认参数单独运行某一种方法：

```bash
./run.sh rasterization
./run.sh ray-casting
./run.sh whitted
./run.sh radiosity
./run.sh path-tracing
```

传入显式参数时执行自定义运行，例如 `./run.sh path-tracing --width 256 --height 256 --spp 64`。

## 渲染结果

以下图片由正式生产实现生成，并从纳入版本控制的 `outputs/` 证据复制而来。再次执行 `./run.sh` 即可刷新。

![五种渲染方法](docs/images/five_methods.png)

![Path Tracing 收敛曲线](docs/images/convergence.png)

![白炉验证](docs/images/white_furnace.png)

如果只想查看 CPU 分配而不渲染：

```bash
./run.sh system-info
```

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

测试覆盖生产配置、几何、光学、能量守恒、五种渲染器、多进程、输出文件和确定性采样。
