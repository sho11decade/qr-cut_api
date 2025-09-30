from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ProcessLog
from ..schemas import ProcessLogEntry

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs", response_model=list[ProcessLogEntry], summary="List recent processing logs")
def list_logs(db: Session = Depends(get_db)) -> list[ProcessLogEntry]:
    logs = db.query(ProcessLog).order_by(ProcessLog.processed_at.desc()).limit(50).all()
    return [ProcessLogEntry.from_orm(log) for log in logs]
