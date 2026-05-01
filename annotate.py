"""Annotate a PNG map image with intersection control points from a JSON file.

Usage: python annotate.py [--rescale] <image.png> <points.json>

Writes <image-annotated.png> next to the input image.

With --rescale, x/y coordinates are scaled from the JSON's width/height to the
actual image dimensions. Requires the JSON to have top-level width and height fields.
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def annotate(image_path: Path, json_path: Path, rescale: bool = False) -> Path:
    with open(json_path) as f:
        data = json.load(f)

    if isinstance(data, list):
        points = data
        scale_x = scale_y = 1.0
    else:
        points = data["points"]
        if rescale:
            img_check = Image.open(image_path)
            actual_w, actual_h = img_check.size
            scale_x = actual_w / data["width"]
            scale_y = actual_h / data["height"]
        else:
            scale_x = scale_y = 1.0

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font = ImageFont.load_default()

    for pt in points:
        x = round(pt["x"] * scale_x)
        y = round(pt["y"] * scale_y)
        r = 10
        draw.ellipse([x - r, y - r, x + r, y + r], fill="red", outline="red")
        draw.text((x + r + 4, y - 14), pt["street1"], fill="red", font=font)
        draw.text((x + r + 4, y + 4), pt["street2"], fill="red", font=font)

    out_path = image_path.with_stem(image_path.stem + "-annotated")
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Annotate a map image with intersection control points."
    )
    parser.add_argument("image", type=Path, help="Input PNG file")
    parser.add_argument("json", type=Path, help="JSON file with control points")
    parser.add_argument(
        "--rescale",
        action="store_true",
        help="Scale coordinates from JSON width/height to image size",
    )
    args = parser.parse_args()

    out_path = annotate(args.image, args.json, rescale=args.rescale)
    print(f"Saved {out_path}")
