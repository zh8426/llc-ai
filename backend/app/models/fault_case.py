from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class FaultCase(Base):
    __tablename__ = "fault_cases"

    case_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    topology: Mapped[str] = mapped_column(String(50), nullable=False)
    power_w: Mapped[float | None] = mapped_column(Float)
    vin_v: Mapped[float | None] = mapped_column(Float)
    vout_v: Mapped[float | None] = mapped_column(Float)
    load_description: Mapped[str | None] = mapped_column(String(300))
    symptom: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    observed_features: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    verification_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fix: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    waveform_before: Mapped[str | None] = mapped_column(Text)
    waveform_after: Mapped[str | None] = mapped_column(Text)
    engineer_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    verification_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
