# Homemade CPU Renderer：产品需求文档

## 1. 项目概述

本项目使用 Python 构建一套纯 CPU、可运行、可对比、可验证的渲染教学工程。工程以经典 Cornell Box 为统一场景，对比五种由简单到完整的渲染方法：

1. Rasterization（光栅化，非光线追踪 baseline）；
2. Ray Casting（光线投射）；
3. Whitted Ray Tracing（经典递归光线追踪）；
4. Radiosity（辐射度算法）；
5. PBR Path Tracing（物理路径追踪）。

项目重点是直观展示不同算法能处理的光路，同时通过解析几何、线性系统残差、能量守恒、白炉测试和 Monte Carlo 收敛曲线验证正确性。

## 2. 核心目标

1. 五种方法各自使用独立目录和入口，避免巨型单文件。
2. 五种方法尽可能使用相同的 Cornell Box 几何、相机、分辨率、材质参数和光源参数。
3. 优先复用成熟 Python 库完成数组运算、网格加载、空间求交、线性求解、图片处理和性能监测，不重复制造与教学目标无关的基础设施。
4. 使用多进程进行 CPU 渲染，默认配置为约 90% 的逻辑 CPU 容量。
5. 提供一个 `run.sh`，可运行单个方法、全部方法、验证流程或 README 截图生成流程。
6. 自动输出五种方法的截图、耗时、验证报告和 Path Tracing 的 SPP/MSE 收敛曲线。
7. 实施时先建立 `.gitignore`，再下载数据或生成任何渲染产物。

### 2.1 Spec 优先级与交付纪律

- 本文档是项目设计、实现、测试和验收的最高依据；实现与 Spec 冲突时，必须停止实现并先修订、确认 Spec。
- 不得为了缩短开发或验证时间而使用 Mock、占位实现、硬编码结果、伪造截图或绕开正式渲染路径。
- 不建立“演示版逻辑”“快速验证逻辑”和“正式逻辑”等多套实现；测试、CLI、截图生成和最终渲染必须调用同一套生产代码。
- 遇到性能问题，应优化正式实现或调整用户明确指定的运行参数，不能用降低正确性、跳过步骤或替换算法的方式走捷径。
- 每项实现都必须可追溯到本文档中的需求和验收标准；未定义或存在歧义的行为必须先确认，不能自行扩展。
- Spec 的变更只能使用增量 Patch，保留已有结构和上下文，不通过整体重写掩盖改动范围。

## 3. 非目标

- 不使用 CUDA、Metal、OpenCL 或 GPU 渲染作为五种方法之一。
- 不追求实时帧率或完整复刻 Blender、Mitsuba 等工业渲染器。
- 第一版不实现动画、体积渲染、光谱渲染、复杂纹理系统或分布式集群渲染。
- 不要求五种算法产生相同图像；它们支持的光路本来就不同。
- 不手写通用网格解析器、图片编码器或通用线性代数库。
- 不允许以 Mock、伪数据或预制图片代替任何正式验证结果。

## 4. 技术栈与库复用

### 4.1 运行环境

- Python 3.11 或更高版本；
- macOS 与常见 Linux 环境优先；
- 所有正式对比结果在 CPU 模式生成；
- 随机算法支持固定 Seed，保证实验可复现。

### 4.2 计划依赖

| 库 | 用途 | 是否必须 |
| --- | --- | --- |
| NumPy | 向量化数学、像素缓冲、射线批处理 | 必须 |
| SciPy | Radiosity 稀疏/稠密线性方程求解 | 必须 |
| Numba | 热点数值循环 JIT 加速 | 必须 |
| Trimesh | Cornell Box 网格加载、变换与网格数据管理 | 必须 |
| Pillow | PNG 写入、缩略图和拼图 | 必须 |
| Matplotlib | MSE、收敛和性能图表 | 必须 |
| tqdm | 渲染进度 | 必须 |
| psutil | CPU 数量、占用信息和资源报告 | 必须 |
| pytest | 单元、集成和回归测试 | 开发必须 |
| Embree/embreex | CPU 加速射线求交 | 可选加速后端 |

库的职责边界：

- Trimesh 负责网格数据，不替代五种渲染算法的核心逻辑；
- NumPy/Numba 负责数值计算和热点加速；
- SciPy 负责可靠求解 Radiosity 方程组；
- Embree 后端存在时用于 BVH/求交加速，不存在时回退到 Trimesh/NumPy CPU 求交；
- 渲染方程、BRDF 权重、光路递归、Form Factor 和能量验证必须在项目代码中清晰可见。

### 4.3 SOLID 与 DRY 架构约束

- **单一职责（SRP）**：场景、几何求交、材质、积分器、并行调度、验证和图片输出分别承担单一职责。
- **开闭原则（OCP）**：新增材质、场景或求交后端应通过稳定接口扩展，避免修改多个既有渲染器。
- **里氏替换（LSP）**：所有材质、光源和求交后端必须满足公共接口契约，替换实现不能改变调用方语义。
- **接口隔离（ISP）**：接口只暴露调用方真正需要的能力，不能用包含大量无关方法的万能基类连接模块。
- **依赖倒置（DIP）**：高层渲染算法依赖场景、求交和输出协议，不直接依赖特定 Trimesh、Embree 或文件格式实现。
- **DRY**：Cornell Box、颜色空间转换、求交结果、材质参数、CPU 配置、图片写入和验证公式各自只有一个事实来源。
- 公共代码只有在语义确实相同且存在稳定复用关系时才抽取；不得为了表面消除重复而混合不同算法的核心步骤。
- 禁止复制后微调形成多份求交、色调映射、随机种子或能量计算逻辑；差异必须通过参数、策略接口或明确的算法实现表达。

### 4.4 中文注释与文档规范

所有项目内编写的 Python、Shell 和配置代码必须以可维护性为首要目标：

- 每个代码文件开头必须包含中文意图注释或模块 Docstring，说明文件职责、输入输出、所属架构层以及明确不负责的内容。
- 每个公开或内部函数、方法和类必须包含完整中文 Docstring，至少说明用途、参数、返回值、异常、副作用、单位/坐标系以及重要前置条件；确实无返回值或无异常时也应清楚说明。
- 对长难句对应的代码段、复杂控制流、数学公式、概率权重、能量变化、并行边界、数值容差和容易误解的关键点添加就近中文注释。
- 注释重点解释设计原因、不变量和陷阱，不能只把代码逐字翻译成中文。
- 变量与 API 标识符使用清晰英文；解释性文字、模块说明和项目自有 Docstring 使用中文，第三方固定术语可保留英文并首次给出中文含义。
- 修改代码时必须同步维护注释；失真、过期或与实现矛盾的注释视为缺陷。
- 不以“代码很简单”为由省略文件意图和函数 Docstring，也不使用自动生成的空泛模板敷衍要求。
- Code Review 和测试验收必须检查注释完整性；缺少必要中文说明的代码不得视为完成。

## 5. 统一 Cornell Box 场景

### 5.1 标准场景

五种方法默认使用同一个 `cornell_box` 场景：

- 白色地面、天花板与后墙；
- 红色左墙与绿色右墙；
- 天花板矩形面光源；
- 一个短方盒与一个高方盒；
- 固定透视相机、视场角和输出分辨率；
- 所有颜色计算在线性空间完成，最终统一进行色调映射与 sRGB 转换。

为了展示 Whitted 与 PBR 材质，可提供 `cornell_box_mixed` 变体，将盒子替换或补充为镜面物体与玻璃物体。主对比图必须注明所用变体，不能暗中改变场景。

### 5.2 场景来源

- 基础 Cornell Box 优先由代码程序化生成，保证离线可运行；
- `scripts/download_data.py` 下载可选 OBJ、参考图或高精度参考结果；
- 下载清单必须记录来源、许可证、目标路径和 SHA-256；
- 下载失败不能阻止基础 Cornell Box 运行。

## 6. 五种渲染方法

### 6.1 Rasterization：非光追 baseline

Rasterization 将三角形投影到屏幕空间，并用 Z-Buffer 解决可见性，不追踪光线。

功能范围：

- Cornell Box 三角网格的 MVP 变换；
- 三角形屏幕空间光栅化与深度测试；
- 环境项、Lambert 直接光和可选 Blinn-Phong 高光；
- 默认不计算真实阴影、反射、折射或间接光；
- 输出速度与画质作为其他方法的 baseline。

实现策略：使用 Trimesh 管理网格，NumPy/Numba 完成小型 CPU 三角形光栅化器和 Z-Buffer；不引入 GPU 图形 API。

验证指标：

- 深度测试与前后遮挡关系正确；
- 投影后的已知顶点位置与解析结果一致；
- 输出无空洞、NaN、Inf 和越界写入。

### 6.2 Ray Casting

功能范围：

- 每像素发射主射线；
- 只计算最近交点、直接光和 Shadow Ray；
- 支持硬阴影；
- 不递归计算反射、折射和间接光。

验证指标：

- 射线与三角形交点和最近命中正确；
- 遮挡存在时 Shadow Ray 正确判断不可见；
- 直接光结果非负且有限。

### 6.3 Whitted Ray Tracing

功能范围：

- 复用 Ray Casting 的直接光与硬阴影；
- 支持理想镜面递归反射；
- 支持理想介质折射、Fresnel-Schlick 和全反射；
- 支持最大递归深度、射线偏移和能量阈值终止。

验证指标：

- 反射满足入射角等于反射角；
- 折射满足 Snell 定律；
- Fresnel 权重与材质权重不会使总能量大于入射能量；
- 递归稳定终止，不出现越弹越亮的非物理发散。

### 6.4 Radiosity

功能范围：

- 将 Cornell Box 漫反射表面离散为 Patches；
- 计算或采样估计 Patch 间 Form Factor；
- 使用 SciPy 建立并求解辐射度方程；
- 将 Patch 辐射度通过公共相机投影成最终图像；
- 展示红绿墙产生的颜色晕染。

验证指标：

- Form Factor 非负；
- 封闭场景每行 Form Factor 之和近似为 1；
- 互易性 `A_i F_ij ≈ A_j F_ji` 在容差内成立；
- 线性方程组残差低于阈值；
- 反射率小于 1 时解有限且非负。

### 6.5 PBR Path Tracing

功能范围：

- 用 Monte Carlo 积分求解渲染方程；
- 支持 Lambertian 漫反射、理想镜面和玻璃介质；
- 支持矩形面光源、多次间接弹跳和俄罗斯轮盘赌；
- 第一版实现 Next Event Estimation；
- MIS 作为优先增强项，在基础正确性完成后加入；
- 支持 1、8、32、128、512 等多档 SPP 和阶段性保存。

验证指标：

- BRDF、余弦项、PDF 和路径吞吐量计算一致；
- 材质的反射、透射与吸收能量总和不超过入射能量；
- White Furnace Test 在统计容差内接近亮度 1；
- 固定场景下，SPP 增加时 MSE 总体下降；
- 对无偏且方差有限的估计，标准误差预期按 `O(1/sqrt(N))` 下降，MSE 预期按 `O(1/N)` 下降；
- 统计噪声允许局部波动，不要求每个 SPP 点严格单调；
- 所有路径吞吐量和像素输出均不得出现 NaN、Inf 或持续性爆亮。

## 7. 多进程与 CPU 资源策略

### 7.1 默认策略

- 使用 `concurrent.futures.ProcessPoolExecutor` 或 `multiprocessing`；
- Rasterization、Ray Casting、Whitted 和 Path Tracing 按图像 Tile 分配任务；
- Radiosity 的 Form Factor 采样可按 Patch 区间分配任务，方程求解交给 SciPy；
- 默认工作进程数：`max(1, floor(logical_cpu_count * 0.90))`；
- `logical_cpu_count` 优先由 psutil 获取，失败时回退到 `os.cpu_count()`；
- CLI 提供 `--cpu-percent` 和 `--workers`，其中显式 `--workers` 优先。

### 7.2 限制与安全性

“90% CPU”表示按逻辑核心数量配置约 90% 的 Worker 容量，不承诺系统监视器中的瞬时占用精确保持 90%。NumPy、SciPy、Numba 或 Embree 可能自行创建线程，因此每个子进程必须限制底层线程数，避免 `进程数 × 库线程数` 造成过度订阅。

要求：

- 默认至少为操作系统和其他程序保留一个逻辑核心；
- 支持 `--cpu-percent 50` 等降载运行方式；
- Worker 数、逻辑核心数、耗时和峰值内存写入 JSON 报告；
- 固定 Seed 时，每个 Tile 使用可推导的独立随机流；
- 子进程失败时主进程明确报错，不静默生成不完整图片。

## 8. 数据、忽略文件与实施顺序

必须遵守以下顺序：

1. 首先创建 `.gitignore`；
2. 再创建工程目录与依赖声明；
3. 再实现 `scripts/download_data.py`；
4. 用户显式运行下载命令后，数据写入 `data/downloads/`；
5. 渲染结果写入 `outputs/`；
6. 验证完成后，精选实际生成图片复制到 `docs/images/`。

`.gitignore` 至少覆盖：

- `data/downloads/`；
- `outputs/`；
- Python、Numba 和 pytest 缓存；
- 虚拟环境；
- 本地系统和编辑器文件。

`docs/images/` 是 README 的受控文档资产，不整体忽略。

## 9. CLI 与 Shell 启动

### 9.1 Python CLI

计划命令：

```bash
python -m renderer render --method rasterization --scene cornell-box
python -m renderer render --method ray-casting --scene cornell-box
python -m renderer render --method whitted --scene cornell-box-mixed
python -m renderer render --method radiosity --scene cornell-box
python -m renderer render --method path-tracing --scene cornell-box --spp 128
python -m renderer compare --scene cornell-box
python -m renderer validate --all
```

公共参数至少包括：

- `--width`、`--height`；
- `--cpu-percent`、`--workers`；
- `--seed`、`--output-dir`。

算法专用参数包括 SPP、最大弹跳深度、Patch 数量和 Form Factor 采样数。

### 9.2 Shell 入口

```bash
./run.sh rasterization
./run.sh ray-casting
./run.sh whitted
./run.sh radiosity
./run.sh path-tracing
./run.sh all
./run.sh validate
./run.sh readme
```

- `all`：生成五种方法的效果图与总对比图；
- `validate`：执行物理、数学和统计验证；
- `readme`：生成 README 所需的精选截图及图表；
- 默认使用 Spec 规定的正式参数和约 90% CPU 容量；
- 高清渲染必须通过显式选项启动，避免意外长时间占用机器。

## 10. 输出与 README

运行产物写入：

- `outputs/renders/<method>/`：五种方法的原始 PNG；
- `outputs/comparisons/`：统一尺寸、带标签的五宫格对比图；
- `outputs/charts/`：SPP/MSE、标准误差、残差和性能曲线；
- `outputs/reports/`：参数、Seed、依赖后端、CPU 配置、耗时和验证结果 JSON。

根目录 README 最终包含：

1. 项目目的和五种方法的光路差异；
2. 安装、数据下载和启动方式；
3. Cornell Box 场景与公平对比规则；
4. 五种方法的实际渲染截图；
5. Path Tracing 的 1/8/32/128/512 SPP 对比；
6. 能量守恒、白炉测试和 MSE 收敛曲线；
7. 耗时、Worker 数和 CPU 配置对比；
8. 库复用说明、已知限制与项目目录。

README 图片必须由当前代码实际生成，不使用手工伪造结果。

## 11. 测试与验收标准

### 11.1 自动测试

- 相机、矩阵、颜色空间与投影测试；
- Rasterization 深度缓冲与三角形覆盖测试；
- 射线三角形求交与阴影测试；
- 反射、折射、Fresnel 与全反射测试；
- Form Factor、互易性和线性系统残差测试；
- BRDF、PDF、能量边界与 White Furnace Test；
- 固定 Seed 的正式渲染图像回归测试；
- 多进程结果完整性与可复现性测试；
- CLI 和输出元数据测试。

### 11.2 首版验收

1. `.gitignore` 在任何下载和渲染产物之前建立；
2. 五种方法均有独立入口，并能渲染 Cornell Box PNG；
3. `./run.sh all` 生成五张方法图和一张总对比图；
4. Rasterization baseline 正确显示几何与 Z-Buffer 遮挡；
5. Ray Casting 正确显示直接光与硬阴影；
6. Whitted 正确显示镜面反射和玻璃折射；
7. Radiosity 显示漫反射颜色晕染并通过残差检查；
8. PBR Path Tracing 显示间接光，并通过能量与统计验证；
9. `./run.sh validate` 输出明确的通过/失败状态和 JSON 报告；
10. 默认 Worker 数遵循约 90% 逻辑核心策略，且避免库线程过度订阅；
11. README 的截图、图表和性能数据由当前实现生成；
12. 所有验证和截图均调用正式生产实现，不存在 Mock 或旁路逻辑；
13. 测试通过，输出无 NaN、Inf、越界写入或未处理异常。

## 12. 实施阶段

### 阶段一：忽略规则与工程骨架

- 首先创建 `.gitignore`；
- 创建依赖声明、CLI、公共场景、输出和测试结构；
- 实现 CPU/Worker 配置与底层线程限制；
- 建立中文注释、SOLID、DRY 和 Spec 可追溯性检查清单。

### 阶段二：Cornell Box 与 baseline

- 建立程序化 Cornell Box 和可选数据下载器；
- 实现 Rasterization baseline；
- 固定公共相机、色彩与输出规范。

### 阶段三：确定性光线方法

- 实现 Ray Casting；
- 实现 Whitted Ray Tracing；
- 完成交点、阴影、反射、折射和能量边界测试。

### 阶段四：全局光照

- 实现 Radiosity 与残差验证；
- 实现 PBR Path Tracing、NEE、白炉测试和 SPP/MSE 实验；
- 接入 Tile 多进程与可选 Embree 求交后端。

### 阶段五：自动化与文档

- 完成 `run.sh` 和对比图生成；
- 运行完整验证和正式截图任务；
- 编写 README，加入实际结果、性能数据和限制说明。

## 13. 主要风险

| 风险 | 应对方式 |
| --- | --- |
| Python CPU 路径追踪较慢 | NumPy/Numba、Tile 多进程和可选 Embree；不绕过正式实现 |
| 多进程与数学库线程叠加 | 子进程限制 BLAS/Numba/Embree 线程数 |
| 五种算法能力不同 | 区分视觉对比、功能边界和算法专属验证 |
| Radiosity Patch 数量导致矩阵过大 | 首版限制 Patch 数并优先使用 SciPy 稀疏求解 |
| Monte Carlo MSE 局部波动 | 固定 Seed、多档 SPP、看整体斜率与统计区间 |
| 外部数据失效 | Cornell Box 可程序化生成，下载数据仅作可选增强 |
| 90% CPU 引发温度或交互卡顿 | 保留至少一个核心并允许 `--cpu-percent` 降载 |

## 14. 实现前仍需确定

1. 是否接受上述依赖，特别是 SciPy、Numba、Trimesh 和 psutil；
2. 可选 Embree 后端是首版要求，还是基础版本完成后的加速项；
3. README 正式截图的目标分辨率与最长可接受渲染时间；
4. `cornell_box_mixed` 使用球体还是三角网格物体展示镜面与玻璃；
5. 外部下载数据的具体来源与许可证。
