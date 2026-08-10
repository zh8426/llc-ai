from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    topology: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Half-Bridge LLC"
    )

    vin_min_v: Mapped[float | None] = mapped_column(Float)
    vin_nom_v: Mapped[float | None] = mapped_column(Float)
    vin_max_v: Mapped[float | None] = mapped_column(Float)
    vout_v: Mapped[float | None] = mapped_column(Float)
    iout_a: Mapped[float | None] = mapped_column(Float)
    pout_w: Mapped[float | None] = mapped_column(Float)
    target_efficiency: Mapped[float | None] = mapped_column(Float)

    lr_h: Mapped[float | None] = mapped_column(Float)
    lm_h: Mapped[float | None] = mapped_column(Float)
    cr_f: Mapped[float | None] = mapped_column(Float)

    fsw_min_hz: Mapped[float | None] = mapped_column(Float)
    fsw_nom_hz: Mapped[float | None] = mapped_column(Float)
    fsw_max_hz: Mapped[float | None] = mapped_column(Float)
    transformer_ratio: Mapped[float | None] = mapped_column(Float)
    dead_time_s: Mapped[float | None] = mapped_column(Float)

    rectification_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Diode Rectification"
    )
    controller_model: Mapped[str | None] = mapped_column(String(200))
    controller_frequency_min_hz: Mapped[float | None] = mapped_column(Float)
    controller_frequency_max_hz: Mapped[float | None] = mapped_column(Float)

    primary_switch_manufacturer: Mapped[str | None] = mapped_column(String(200))
    primary_switch_part_number: Mapped[str | None] = mapped_column(String(200))
    primary_switch_vds_rating_v: Mapped[float | None] = mapped_column(Float)
    primary_switch_measured_vds_peak_v: Mapped[float | None] = mapped_column(Float)
    primary_switch_current_rating_a: Mapped[float | None] = mapped_column(Float)
    primary_switch_measured_peak_current_a: Mapped[float | None] = mapped_column(Float)
    primary_switch_current_temperature_condition: Mapped[str | None] = mapped_column(
        String(500)
    )

    resonant_capacitor_voltage_rating_v: Mapped[float | None] = mapped_column(Float)
    resonant_capacitor_voltage_stress_v: Mapped[float | None] = mapped_column(Float)
    resonant_capacitor_rms_current_rating_a: Mapped[float | None] = mapped_column(Float)
    resonant_capacitor_rms_current_stress_a: Mapped[float | None] = mapped_column(Float)

    zvs_analysis_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    full_gain_review_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    output_power_relative_tolerance: Mapped[float | None] = mapped_column(Float)
    measured_vds_required_margin_ratio: Mapped[float | None] = mapped_column(Float)
    gain_review_required_parameters: Mapped[list[str] | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
