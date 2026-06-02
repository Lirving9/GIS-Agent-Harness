from __future__ import annotations

from html import escape
from pathlib import Path


def build_cog_viewer(*, output_html: str | Path, cog_url: str, title: str = "COG Review") -> Path:
    output_path = Path(output_html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; background: #0e1612; color: #eff7ef; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 32px; }}
    .panel {{ border: 1px solid #385244; border-radius: 16px; padding: 24px; background: #142119; }}
    code {{ color: #b7e3c3; }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(title)}</h1>
    <section class="panel" data-viewer="cog-webgl" data-cog-url="{escape(cog_url)}">
      <p>Cloud Optimized GeoTIFF review manifest.</p>
      <p>COG URL: <code>{escape(cog_url)}</code></p>
      <p>Client adapters: geotiff.js, deck.gl, Mapbox GL JS compatible.</p>
    </section>
  </main>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path
