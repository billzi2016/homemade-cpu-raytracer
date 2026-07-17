# Render parameters

`default.toml` is the single default configuration loaded by `./run.sh` when no command-line arguments are supplied.

The committed preset renders the five-method comparison at 512×512. Path Tracing uses
128 samples per pixel, while the smaller convergence reference uses 1024 samples per
pixel. These values favor a clean, verifiable result without the much longer runtime of
a 1024×1024 production render.

The other four methods use independent quality controls: Rasterization, Ray Casting,
and Whitted use 3×3 deterministic supersampling; Whitted uses subdivision-3 smooth
Icospheres; Radiosity uses three Patch subdivision levels and material-safe vertex
radiance interpolation. None of these settings multiplies Path Tracing's 128 SPP.

The `[readme]` table controls the complete production workflow:

- `width` and `height`: final five-method image dimensions;
- `samples_per_pixel`: Path Tracing SPP for the main comparison;
- `reference_spp`: high-SPP reference used by the MSE experiment;
- `convergence_size`: independent square resolution for the statistical experiment;
- `deterministic_samples_per_pixel`: square-grid antialiasing for the deterministic image methods;
- `sphere_subdivisions`: Whitted mirror/glass Icosphere geometry density;
- `radiosity_subdivision_levels`: physical Patch refinement before the linear solve;
- `tile_size`: shared square Tile edge length used to control multiprocessing overhead;
- `cpu_percent`: logical CPU capacity requested by the process scheduler;
- `seed`: deterministic base random seed;
- `output_root`: committed render and report directory;
- `docs_root`: images referenced by the English and Chinese README files.

Explicit CLI arguments remain available for individual experiments, but the default GitHub result set is always reproducible with:

```bash
./run.sh
```

Each production method can load exactly the same preset independently:

```bash
./run.sh rasterization
./run.sh ray-casting
./run.sh whitted
./run.sh radiosity
./run.sh path-tracing
```

Passing explicit options switches that one command to custom CLI parameters, for example
`./run.sh path-tracing --width 256 --height 256 --spp 64`.

The command displays an overall five-method progress bar plus a Tile or Patch progress
bar for the active method. Both use tqdm's elapsed time, processing rate, and ETA.
