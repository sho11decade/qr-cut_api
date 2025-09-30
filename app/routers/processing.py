from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import ProcessLog
from ..schemas import OutputFormat, ProcessResponse, ProcessedImage, ProcessingOptions, Shape
from ..services.qr_processor import QRProcessingError, process_image
from ..utils.file_ops import build_metadata_header, make_storage_filename, persist_bytes

router = APIRouter(prefix="/api", tags=["processing"])


@dataclass
class ProcessedPayload:
    data: bytes
    filename: str
    content_type: str


@router.post("/process", summary="Detect QR codes and mask them in uploaded images")
async def process_images(
    files: list[UploadFile] = File(..., description="Images containing QR codes."),
    fill_color: str = Form("#000000"),
    opacity: float = Form(1.0),
    shape: str = Form("rectangle"),
    output_format: str = Form("PNG"),
    db: Session = Depends(get_db),
) -> Response:
    if not files:
        raise HTTPException(status_code=400, detail="At least one image must be provided.")

    normalized_shape = cast(Shape, shape.lower())
    normalized_format = cast(OutputFormat, output_format.upper())

    try:
        options = ProcessingOptions(
            fill_color=fill_color,
            opacity=opacity,
            shape=normalized_shape,
            output_format=normalized_format,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    processed_records: list[ProcessedImage] = []
    payloads: list[ProcessedPayload] = []

    for upload in files:
        data = await upload.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"File '{upload.filename}' is empty.")

        base_name = Path(upload.filename or "image").stem or "image"
        original_suffix = Path(upload.filename or "").suffix.lstrip(".")
        original_storage_name = make_storage_filename(base_name, original_suffix)
        processed_storage_name = make_storage_filename(base_name, options.output_format.lower())
        source_filename = upload.filename or original_storage_name

        try:
            processed_bytes, qr_count = process_image(data, source_filename, options)
        except QRProcessingError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        persist_bytes(settings.storage_root / "uploads", original_storage_name, data)
        processed_path = persist_bytes(
            settings.storage_root / "processed",
            processed_storage_name,
            processed_bytes,
        )

        log = ProcessLog(
            original_filename=source_filename,
            processed_filename=processed_path.name,
            qr_count=qr_count,
            fill_color=options.fill_color,
            fill_shape=options.shape,
            opacity=options.opacity,
            output_format=options.output_format,
        )
        db.add(log)
        db.commit()

        processed_records.append(
            ProcessedImage(
                original_filename=source_filename,
                processed_filename=processed_path.name,
                qr_count=qr_count,
            ),
        )
        payloads.append(
            ProcessedPayload(
                data=processed_bytes,
                filename=processed_storage_name,
                content_type="image/png" if options.output_format == "PNG" else "image/jpeg",
            ),
        )

    archive_name: str | None = None
    if len(payloads) == 1:
        payload = payloads[0]
        content = payload.data
        media_type = payload.content_type
        download_name = payload.filename
    else:
        archive_name = make_storage_filename("qr-cut", "zip")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in payloads:
                archive.writestr(item.filename, item.data)
        content = zip_buffer.getvalue()
        media_type = "application/zip"
        download_name = archive_name

    response_payload = ProcessResponse(images=processed_records, archive=archive_name)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{download_name}\"",
        "X-QR-Cut-Metadata": build_metadata_header(response_payload.dict()),
    }

    return Response(content=content, media_type=media_type, headers=headers)
