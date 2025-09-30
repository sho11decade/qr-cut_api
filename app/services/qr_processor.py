from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Iterable, List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageColor, ImageDraw

from ..schemas import ProcessingOptions

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except ImportError:  # pragma: no cover - optional dependency
    pyzbar_decode = None


@dataclass
class QRRegion:
    points: np.ndarray


class QRProcessingError(Exception):
    """Raised when an image cannot be processed."""


def _detect_with_pyzbar(image: np.ndarray) -> List[QRRegion]:
    regions: List[QRRegion] = []
    if pyzbar_decode is None:
        return regions
    try:
        decoded = pyzbar_decode(image)
    except Exception:  # pragma: no cover - pyzbar edge failures
        return regions

    for item in decoded:
        polygon = getattr(item, "polygon", None)
        if not polygon:
            continue
        points = np.array([(point.x, point.y) for point in polygon], dtype=np.float32)
        if points.size:
            regions.append(QRRegion(points=points))
    return regions


def _detect_with_opencv(image: np.ndarray) -> List[QRRegion]:
    regions: List[QRRegion] = []
    detector = cv2.QRCodeDetector()
    try:
        ok, decoded, points, _ = detector.detectAndDecodeMulti(image)
    except Exception as exc:  # pragma: no cover - OpenCV internal errors
        raise QRProcessingError("Unable to run QR detection") from exc

    if not ok or points is None:
        return regions

    for polygon in points:
        region = np.array(polygon, dtype=np.float32).reshape(-1, 2)
        if region.size:
            regions.append(QRRegion(points=region))
    return regions


def detect_qr_regions(image: np.ndarray) -> List[QRRegion]:
    regions = _detect_with_pyzbar(image)
    if regions:
        return regions
    return _detect_with_opencv(image)


def _ensure_rgba(image: Image.Image) -> Image.Image:
    return image if image.mode == "RGBA" else image.convert("RGBA")


def _parse_color(color: str, opacity: float) -> Tuple[int, int, int, int]:
    if color.lower() == "transparent":
        return (0, 0, 0, 0)
    try:
        rgba = ImageColor.getcolor(color, "RGBA")
    except ValueError as exc:
        raise QRProcessingError(f"Unsupported color value: {color}") from exc
    alpha = int(max(0.0, min(1.0, opacity)) * 255)
    return (rgba[0], rgba[1], rgba[2], alpha if len(rgba) < 4 else int(rgba[3] * opacity))


def _draw_region(draw: ImageDraw.ImageDraw, region: QRRegion, color: Tuple[int, int, int, int], shape: str) -> None:
    points = region.points
    min_x, min_y = np.min(points, axis=0)
    max_x, max_y = np.max(points, axis=0)
    bbox = [int(min_x), int(min_y), int(max_x), int(max_y)]
    if shape == "ellipse":
        draw.ellipse(bbox, fill=color)
        return
    draw.rectangle(bbox, fill=color)


def mask_regions(image: Image.Image, regions: Iterable[QRRegion], options: ProcessingOptions) -> Image.Image:
    rgba_image = _ensure_rgba(image)
    overlay = Image.new("RGBA", rgba_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    color = _parse_color(options.fill_color, options.opacity)
    for region in regions:
        _draw_region(draw, region, color, options.shape)
    composited = Image.alpha_composite(rgba_image, overlay)
    if options.output_format == "JPEG":
        return composited.convert("RGB")
    return composited


def process_image(data: bytes, filename: str, options: ProcessingOptions) -> Tuple[bytes, int]:
    try:
        with Image.open(io.BytesIO(data)) as image:
            rgb_image = image.convert("RGB")
    except Exception as exc:
        raise QRProcessingError("Invalid image data") from exc

    cv_image = cv2.cvtColor(np.array(rgb_image), cv2.COLOR_RGB2BGR)
    regions = detect_qr_regions(cv_image)
    if not regions:
        masked = rgb_image if options.output_format == "JPEG" else rgb_image.convert("RGBA")
    else:
        masked = mask_regions(rgb_image, regions, options)

    buffer = io.BytesIO()
    save_kwargs: dict[str, Any] = {"format": options.output_format}
    if options.output_format == "JPEG":
        save_kwargs["quality"] = 95
    masked.save(buffer, **save_kwargs)
    return buffer.getvalue(), len(regions)
