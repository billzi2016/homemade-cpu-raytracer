# Homemade CPU Renderer

[简体中文](README.zh-CN.md)

A maintainable, pure-CPU rendering project that compares five rendering methods in a shared Cornell Box. The project treats mathematical and physical validation as first-class output: an image is not considered correct merely because it looks plausible.

## Rendering methods

| Method | Visibility model | Supported light transport | Primary validation |
| --- | --- | --- | --- |
| Rasterization | Triangle projection and Z-buffer | Local direct lighting | Projection and depth ordering |
| Ray Casting | Primary and shadow rays | Direct lighting and hard shadows | Analytic ray intersections |
| Whitted Ray Tracing | Recursive deterministic rays | Direct light, ideal reflection, ideal refraction | Reflection, Snell's law, and bounded throughput |
| Radiosity | Patch-to-patch energy exchange | Diffuse global illumination and color bleeding | Form-factor reciprocity and linear-system residual |
| PBR Path Tracing | Monte Carlo rendering equation | Mixed direct and indirect transport | Energy conservation, white furnace, and MSE convergence |

Rasterization is the non-ray-traced baseline. All five methods use the same scene definitions, camera, linear color pipeline, output encoding, and resource policy wherever their mathematical models permit a fair comparison.

## Why a Cornell Box?

The Cornell Box keeps the geometry understandable while exposing the differences that matter:

- hard visibility and depth ordering;
- direct illumination and shadows;
- ideal mirror reflection and dielectric refraction;
- diffuse interreflection and red/green color bleeding;
- stochastic convergence under increasing samples per pixel (SPP).

The canonical scene is generated programmatically so the core project remains reproducible offline. Optional reference assets may be downloaded separately with recorded provenance, licensing, and SHA-256 checksums.

## Correctness before appearance

The project validates production implementations directly. It does not use mock renderers, hard-coded result images, test-only algorithms, or alternate “quick validation” paths.

The final result set will preserve:

- rendered images for all five methods;
- a labeled five-method comparison;
- Path Tracing results at multiple SPP levels;
- MSE and standard-error convergence charts;
- white-furnace and energy-conservation reports;
- Radiosity form-factor and solver-residual reports;
- CPU, worker-count, memory, seed, and timing metadata.

Validated results are stored under `outputs/` and committed to the repository. README figures are derived from those real outputs rather than handcrafted illustrations.

## CPU resource policy

Rendering uses process-level parallelism. By default, the worker count is computed as approximately 90% of the visible logical CPUs while retaining at least one logical CPU for the operating system on multicore machines.

Each worker limits BLAS, NumExpr, Numba, and related numerical backends to avoid nested thread oversubscription. The reported “90%” is a capacity policy based on logical CPU count, not a promise that an operating-system monitor will remain at exactly 90% utilization every instant.

## Installation

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
```

The optional Embree-compatible CPU intersection backend can be installed with:

```bash
python3 -m pip install -e '.[dev,embree]'
```

## Current executable interface

The shared project foundation is implemented and tested. The current production CLI can inspect the actual CPU allocation policy:

```bash
python3 -m renderer system-info --cpu-percent 90
```

Example output from a 24-logical-CPU host:

```json
{"cpu_percent": 90.0, "logical_cpus": 24, "workers": 21}
```

Rendering commands and images will be documented here only after their production implementations and validations are complete.

## Architecture

```text
src/renderer/
├── core/          # Rays, color transforms, and shared numerical contracts
├── geometry/      # Mesh adapters, projection, and intersection backends
├── materials/     # Diffuse, mirror, and dielectric material contracts
├── lights/        # Point and area emitters
├── scenes/        # Shared Cornell Box and white-furnace scenes
├── methods/       # Five independent rendering algorithms
├── parallel/      # Worker policy, thread limits, tiles, and deterministic seeds
├── validation/    # Geometry, energy, radiosity, furnace, and convergence checks
└── output/        # PNG encoding, charts, montages, and run metadata
```

The architecture follows SOLID and DRY principles without forcing mathematically different algorithms into a misleading common implementation. Shared scene, geometry, color, resource, output, and validation rules have one source of truth; each method retains its genuinely distinct rendering logic.

## Documentation and code quality

Every project-owned code file begins with a Chinese module-intent description. Functions, methods, and classes include Chinese documentation covering parameters, return values, exceptions, side effects, units, coordinate systems, and relevant preconditions. Complex formulas, numerical tolerances, energy weights, random sampling, and multiprocessing boundaries include nearby Chinese rationale.

The governing requirements and planned file ownership are available in:

- [`specs/PRD.md`](specs/PRD.md)
- [`specs/PROJECT_TREE.md`](specs/PROJECT_TREE.md)

## Tests

Run the production contract tests with:

```bash
PYTHONPATH=src python3 -m pytest -p no:cacheprovider tests
```

The current foundation tests cover configuration validation, normalized immutable rays, linear-to-sRGB output, worker allocation, exact Tile coverage, and deterministic independent seed derivation.
