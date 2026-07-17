# 项目目录规划

以下是目标结构。五种方法各自拥有目录，同时复用 Cornell Box、网格、材质、多进程和输出模块。

```text
homemade-cpu-raytracer/
├── .gitignore                         # 第一项实施内容
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── run.sh
├── specs/
│   ├── PRD.md
│   └── PROJECT_TREE.md
├── src/
│   └── renderer/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── core/
│       │   ├── camera.py
│       │   ├── color.py
│       │   ├── ray.py
│       │   └── types.py
│       ├── geometry/
│       │   ├── mesh.py               # Trimesh 适配层
│       │   ├── intersection.py       # Trimesh/Embree 后端
│       │   └── projection.py
│       ├── materials/
│       │   ├── base.py
│       │   ├── diffuse.py
│       │   ├── dielectric.py
│       │   └── mirror.py
│       ├── lights/
│       │   ├── area.py
│       │   └── point.py
│       ├── scenes/
│       │   ├── scene.py
│       │   ├── registry.py
│       │   ├── cornell_box.py
│       │   ├── cornell_box_mixed.py
│       │   └── white_furnace.py
│       ├── methods/
│       │   ├── rasterization/
│       │   │   ├── renderer.py
│       │   │   ├── shading.py
│       │   │   └── zbuffer.py
│       │   ├── ray_casting/
│       │   │   ├── renderer.py
│       │   │   └── shading.py
│       │   ├── whitted/
│       │   │   ├── fresnel.py
│       │   │   ├── optics.py
│       │   │   └── renderer.py
│       │   ├── radiosity/
│       │   │   ├── form_factors.py
│       │   │   ├── patches.py
│       │   │   ├── renderer.py
│       │   │   └── solver.py
│       │   └── path_tracing/
│       │       ├── bsdf.py
│       │       ├── integrator.py
│       │       ├── renderer.py
│       │       └── sampling.py
│       ├── parallel/
│       │   ├── resources.py          # 90% CPU/Worker 计算
│       │   ├── seeds.py              # 可复现独立随机流
│       │   ├── thread_limits.py      # 防止底层库过度订阅
│       │   └── tiles.py
│       ├── validation/
│       │   ├── convergence.py
│       │   ├── energy.py
│       │   ├── geometry.py
│       │   ├── radiosity.py
│       │   └── white_furnace.py
│       └── output/
│           ├── charts.py
│           ├── image.py
│           ├── metadata.py
│           └── montage.py
├── scripts/
│   ├── download_data.py
│   ├── generate_comparison.py
│   └── publish_readme_images.py
├── tests/
│   ├── unit/
│   │   ├── test_projection.py
│   │   ├── test_zbuffer.py
│   │   ├── test_intersection.py
│   │   ├── test_optics.py
│   │   ├── test_radiosity.py
│   │   ├── test_sampling.py
│   │   └── test_resources.py
│   ├── integration/
│   │   ├── test_cli.py
│   │   ├── test_renderers.py
│   │   ├── test_multiprocessing.py
│   │   └── test_validation.py
│   └── regression/
│       └── test_small_images.py
├── data/
│   ├── README.md
│   ├── manifest.json                 # 来源、许可证、SHA-256
│   └── downloads/                    # 下载生成，Git 忽略
├── outputs/                          # 正式渲染与验证结果，纳入版本控制
│   ├── renders/
│   │   ├── rasterization/
│   │   ├── ray_casting/
│   │   ├── whitted/
│   │   ├── radiosity/
│   │   └── path_tracing/
│   ├── comparisons/
│   ├── charts/
│   └── reports/
└── docs/
    └── images/                       # README 精选实际结果
        ├── five_methods.png
        ├── path_tracing_spp.png
        ├── convergence.png
        └── white_furnace.png
```

## 模块边界

### 公共层

`core/`、`geometry/`、`materials/`、`lights/` 和 `scenes/` 保存五种方法共享的数据。Cornell Box 只能定义一次，各渲染方法通过适配接口读取同一场景，避免参数漂移。

### 方法层

- `rasterization/`：非光追 baseline，屏幕空间三角形与 Z-Buffer；
- `ray_casting/`：主射线、直接光与硬阴影；
- `whitted/`：确定性镜面反射和介质折射递归；
- `radiosity/`：Patch、Form Factor 和 SciPy 线性求解；
- `path_tracing/`：BRDF 采样、NEE 与 Monte Carlo 路径积分。

每种方法有独立 `renderer.py`，但不能复制公共场景和输出实现。

### 并行层

`parallel/` 统一管理 Tile、多进程 Worker、随机种子和底层库线程限制。默认 Worker 数约为逻辑核心的 90%，同时至少保留一个核心。

### 验证与输出层

`validation/` 输出数值指标和机器可读结论；`output/` 统一管理线性色彩、色调映射、PNG、图表、拼图和元数据，保证五种方法的展示标准一致。

## 文件生成顺序

1. 创建 `.gitignore`；
2. 创建项目骨架与依赖文件；
3. 创建下载器和数据清单；
4. 下载可选数据到 `data/downloads/`；
5. 生成并验证正式结果到 `outputs/`，随后纳入版本控制；
6. 将验证后的精选结果发布到 `docs/images/`。

下载与渲染均应由用户显式命令触发，不在导入 Python 包时产生文件或网络请求。

`outputs/` 保存 README 所引用的真实渲染图、对比图、曲线和验证报告，不得写入 `.gitignore`。临时帧和失败产物应使用系统临时目录或明确的临时子目录，并在正式发布前清理，避免与可复查结果混淆。

## SOLID 与 DRY 落地规则

- `methods/` 只保存各算法真正不同的核心逻辑；公共相机、场景、求交、颜色和输出不得在方法目录内复制实现。
- `geometry/intersection.py` 通过协议隔离 Trimesh/Embree 后端，渲染器不得直接绑定具体第三方求交类。
- `parallel/` 是 Worker 数、Tile、随机流和线程限制的唯一事实来源，任何方法不得私自创建另一套进程管理逻辑。
- `output/` 是色调映射、sRGB 转换、图片写入和元数据格式的唯一事实来源。
- `validation/` 必须调用正式生产模块，不建立用于通过测试的替代算法、Mock 渲染器或硬编码参考结果。
- 共享抽象必须具有明确职责和稳定契约；不能用万能工具类把无关功能堆积在一起。

## 中文注释检查规则

- 每个代码文件开头具有中文模块意图说明，写明职责、输入输出、架构位置和非职责范围。
- 每个函数、方法和类具有完整中文 Docstring，覆盖参数、返回值、异常、副作用、单位、坐标系和前置条件。
- 数学公式、能量权重、随机采样、数值容差、多进程边界及复杂控制流具有就近中文解释。
- 注释必须解释原因、不变量和风险，不得机械复述语句。
- 修改实现时同步修改注释；注释不完整或与代码不一致时不得通过验收。

## 唯一正式执行路径

CLI、`run.sh`、测试、验证报告和 README 截图生成均调用同一套 `src/renderer/` 生产实现。项目不设置快速版、演示版、Mock 版或仅供测试的第二套渲染逻辑；性能优化必须发生在正式代码路径内。

## Git 提交规范

- 提交前检查完整差异，只包含当前任务相关文件。
- Commit 主题使用简洁、明确的中文祈使描述，正文解释动机与关键约束。
- 一次 Commit 聚焦一个逻辑变更，不混入下载数据、缓存、渲染产物或无关格式化。
- Commit 信息总计不超过 10 行，避免冗长流水账，也不能只写“更新”“修复”等无信息内容。
