"""Annotate a PNG map image with intersection control points from a JSON file.

Usage: python annotate.py <image.png> <points.json>

Writes <image-annotated.png> next to the input image.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def annotate(image_path: Path, json_path: Path) -> Path:
    with open(json_path) as f:
        data = json.load(f)

    points = data if isinstance(data, list) else data["points"]

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font = ImageFont.load_default()

    for pt in points:
        x, y = pt["x"], pt["y"]
        r = 10
        draw.ellipse([x - r, y - r, x + r, y + r], fill="red", outline="red")
        draw.text((x + r + 4, y - 14), pt["street1"], fill="red", font=font)
        draw.text((x + r + 4, y + 4), pt["street2"], fill="red", font=font)

    out_path = image_path.with_stem(image_path.stem + "-annotated")
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <image.png> <points.json>")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    json_path = Path(sys.argv[2])
    out_path = annotate(image_path, json_path)
    print(f"Saved {out_path}")
