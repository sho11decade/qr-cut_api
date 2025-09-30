from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String, func

from .database import Base


class ProcessLog(Base):
    __tablename__ = "process_logs"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String, nullable=False)
    processed_filename = Column(String, nullable=False)
    qr_count = Column(Integer, nullable=False)
    fill_color = Column(String, nullable=False)
    fill_shape = Column(String, nullable=False)
    opacity = Column(Float, nullable=False)
    output_format = Column(String, nullable=False)
    processed_at = Column(DateTime, server_default=func.now(), nullable=False)
