from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReviewRun(Base):
    __tablename__ = "review_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pass_count: Mapped[int] = mapped_column(Integer, nullable=False)
    info_count: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False)
    insufficient_data_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    findings: Mapped[list["ReviewFinding"]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewFinding.position",
    )
    project_snapshot: Mapped["ReviewProjectSnapshot | None"] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ReviewFinding(Base):
    __tablename__ = "review_findings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    review_id: Mapped[str] = mapped_column(
        ForeignKey("review_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    calculated_values: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    missing_information: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    recommended_action: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    requires_engineer_confirmation: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    report_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)

    review: Mapped[ReviewRun] = relationship(back_populates="findings")


class ReviewProjectSnapshot(Base):
    __tablename__ = "review_project_snapshots"

    review_id: Mapped[str] = mapped_column(
        ForeignKey("review_runs.id", ondelete="CASCADE"), primary_key=True
    )
    project_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)

    review: Mapped[ReviewRun] = relationship(back_populates="project_snapshot")
