from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, validator


ColorString = str
Shape = Literal["rectangle", "ellipse"]
OutputFormat = Literal["PNG", "JPEG"]


class ProcessingOptions(BaseModel):
    fill_color: ColorString = Field("#000000", description="Color used to mask QR regions.")
    opacity: float = Field(1.0, ge=0.0, le=1.0, description="Mask opacity between 0 and 1.")
    shape: Shape = Field("rectangle", description="Mask shape.")
    output_format: OutputFormat = Field("PNG", description="Output image format.")

    @validator("fill_color")
    def validate_fill_color(cls, value: str) -> str:  # noqa: N805
        if not value:
            raise ValueError("fill_color must not be empty")
        return value


class ProcessedImage(BaseModel):
    original_filename: str
    processed_filename: str
    qr_count: int


class ProcessResponse(BaseModel):
    images: List[ProcessedImage]
    archive: Optional[str] = Field(
        default=None,
        description="Filename of the archive when multiple images were processed.",
    )


class ProcessLogEntry(BaseModel):
    id: int
    original_filename: str
    processed_filename: str
    qr_count: int
    fill_color: str
    fill_shape: str
    opacity: float
    output_format: str
    processed_at: datetime

    class Config:
        orm_mode = True
