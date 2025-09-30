from __future__ import annotations

import io
import json
import zipfile

from typing import cast

import qrcode
from PIL import Image


def _make_qr_bytes(payload: str = "https://example.com") -> bytes:
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    pil_image = cast(Image.Image, qr.make_image(fill_color="black", back_color="white"))
    image = pil_image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_process_single_image_returns_masked_image_and_metadata(client):
    image_bytes = _make_qr_bytes()

    response = client.post(
        "/api/process",
        data={
            "fill_color": "#000000",
            "opacity": "1.0",
            "shape": "rectangle",
            "output_format": "PNG",
        },
        files=[("files", ("qr.png", image_bytes, "image/png"))],
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")

    metadata = json.loads(response.headers["X-QR-Cut-Metadata"])
    assert metadata["images"], "Metadata should include processed images"
    assert metadata["images"][0]["qr_count"] >= 1
    logs_response = client.get("/api/logs")
    assert logs_response.status_code == 200
    logs = logs_response.json()
    assert len(logs) == 1
    assert logs[0]["qr_count"] >= 1


def test_process_multiple_images_returns_archive(client):
    image_one = _make_qr_bytes("https://example.com/1")
    image_two = _make_qr_bytes("https://example.com/2")

    response = client.post(
        "/api/process",
        data={
            "fill_color": "#ffffff",
            "opacity": "0.8",
            "shape": "ellipse",
            "output_format": "PNG",
        },
        files=[
            ("files", ("qr1.png", image_one, "image/png")),
            ("files", ("qr2.png", image_two, "image/png")),
        ],
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    archive_bytes = io.BytesIO(response.content)
    with zipfile.ZipFile(archive_bytes) as archive:
        names = archive.namelist()
        assert len(names) == 2

    metadata = json.loads(response.headers["X-QR-Cut-Metadata"])
    assert metadata["archive"] is not None
    assert len(metadata["images"]) == 2
