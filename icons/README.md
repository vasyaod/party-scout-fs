# City emblem icons

Source assets + a resolution cache for each city's emblem (shown in the site's city
picker / header). One folder per city `slug`:

```
icons/<slug>/
  original.png     1024×1024 RGBA — the source (AI-generated, transparent)
  <slug>.svg       scalable wrapper that embeds original.png (source art is raster)
  512.png 256.png 128.png 64.png 48.png 32.png 24.png   cached square downscales
```

- **san-francisco** — Golden Gate towers + fog (neon purple/magenta).
- **los-angeles** — palm trees + sunset + skyline.

The live UI loads a small display copy from the site root (`/city-<slug>.png`); this
folder is the **original + SVG + extra-resolution cache** to pull from whenever a
different size is needed. Regenerate the downscales from `original.png` with PIL
(`Image.resize(..., LANCZOS)`). Keep the neon-purple `#7c5cff`/`#c86bff` palette and a
transparent background when adding a new city's emblem.

## Mascot

`icons/owl/` — the Party Scout owl badge:
- `original.png` — the source raster mascot (512×512).
- `owl.svg` — a **true vector** trace of it (via vtracer, multi-color). Scales
  infinitely; the soft outer glow of the raster is flattened. ~460 KB.
