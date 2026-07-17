# Optional data

The Cornell Box and white-furnace scene are generated directly by the production Python code and require no download.

`manifest.json` is reserved for optional external OBJ files or reference images. Every future entry must include its source URL, repository-relative destination, license, and SHA-256 checksum. Downloaded files are written to `data/downloads/` and are not committed.

```bash
python3 scripts/download_data.py
```
