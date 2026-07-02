"""SQLAlchemy 2.0 ORM models for Pain Goblin – redesigned data flow.

* Opportunity is produced by an **Arbitration** step that consumes one or more
  **Analysis** rows (one per provider/model).
* Important analysis fields are normalised into columns; provider‑specific
  payloads stay in ``raw_response`` / ``extra`` JSONB columns.
* Operational metadata (pipeline runs, retries, cost, latency, failures) is
  captured in dedicated tables so the system is fully observable.
* **Report** and **Delivery** are separate – a report can be delivered through
  many channels (Telegram, e‑mail, Slack, …) and a channel can be retried.
* Providers / models are stored as free‑form strings (provider, model, version)
  instead of hard‑coded enums – future‑proof for new vendors.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .models import (
        Analysis,
        Arbitration,
        Delivery,
        Opportunity,
        PipelineRun,
        Post,
        Report,
    )


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# Enums (kept small – only truly static vocabularies)
# ---------------------------------------------------------------------------
class PostStatus(PyEnum):
    NEW = "NEW"
    ANALYZED = "ANALYZED"
    ARBITRATED = "ARBITRATED"
    REPORTED = "REPORTED"
    FAILED = "FAILED"


class RunStatus(PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class DeliveryStatus(PyEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class DeliveryChannel(PyEnum):
    TELEGRAM = "TELEGRAM"
    EMAIL = "EMAIL"
    SLACK = "SLACK"
    WEBHOOK = "WEBHOOK"


class ReportType(PyEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    AD_HOC = "AD_HOC"


# ---------------------------------------------------------------------------
# Core domain tables
# ---------------------------------------------------------------------------
class Post(Base):
    """Raw post collected from a source (Reddit, RSS, HN, …)."""

    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    feed_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    status: Mapped[PostStatus] = mapped_column(
        SQLEnum(PostStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=PostStatus.NEW,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    analyses: Mapped[List["Analysis"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    arbitration: Mapped[Optional["Arbitration"]] = relationship(
        back_populates="post", uselist=False, lazy="selectin"
    )
    opportunity: Mapped[Optional["Opportunity"]] = relationship(
        back_populates="post", uselist=False, lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("url", "source", name="uq_post_url_source"),
        Index("ix_post_status_created", "status", "created_at"),
        Index("ix_post_source_created", "source", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Post(id={self.id}, source={self.source}, status={self.status.value})>"


class Analysis(Base):
    """Single provider/model analysis of a post."""

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Provider identification – free‑form to stay future‑proof
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)   # e.g. "deepseek", "gemini"
    model: Mapped[str] = mapped_column(String(100), nullable=False)                 # e.g. "deepseek-chat", "gemini-1.5-pro"
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # e.g. "2024-06-01"

    # Normalised, provider‑agnostic fields (nullable – not every provider returns all)
    pain_points: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    severity: Mapped[Optional[int]] = mapped_column(nullable=True)          # 1‑5
    frequency: Mapped[Optional[int]] = mapped_column(nullable=True)         # 1‑5
    urgency: Mapped[Optional[int]] = mapped_column(nullable=True)           # 1‑5
    monetizability: Mapped[Optional[int]] = mapped_column(nullable=True)    # 1‑5
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    automation_potential: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Full raw response + any provider‑specific extras
    raw_response: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    extra: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Operational metadata
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)   # 0.0‑1.0
    cost_usd: Mapped[float] = mapped_column(nullable=False, default=0.0)
    latency_ms: Mapped[int] = mapped_column(nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[RunStatus] = mapped_column(
        SQLEnum(RunStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=RunStatus.PENDING,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    post: Mapped["Post"] = relationship(back_populates="analyses", lazy="selectin")
    arbitration: Mapped[Optional["Arbitration"]] = relationship(
        back_populates="analyses", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_analysis_provider_model_created", "provider", "model", "created_at"),
        Index("ix_analysis_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Analysis(id={self.id}, provider={self.provider}, model={self.model}, status={self.status.value})>"


class Arbitration(Base):
    """Cross‑model consensus for a single post – produces the Opportunity."""

    __tablename__ = "arbitrations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Normalised consensus fields (these become the Opportunity columns)
    pain_points: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    severity: Mapped[int] = mapped_column(nullable=False)          # 1‑5
    frequency: Mapped[int] = mapped_column(nullable=False)         # 1‑5
    urgency: Mapped[int] = mapped_column(nullable=False)           # 1‑5
    monetizability: Mapped[int] = mapped_column(nullable=False)    # 1‑5
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    automation_potential: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    score: Mapped[float] = mapped_column(nullable=False, index=True)   # composite ranking
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)  # consensus confidence

    # Disagreement diagnostics
    disagreement_flag: Mapped[bool] = mapped_column(nullable=False, default=False)
    disagreement_details: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Operational metadata
    status: Mapped[RunStatus] = mapped_column(
        SQLEnum(RunStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=RunStatus.PENDING,
        index=True,
    )
    cost_usd: Mapped[float] = mapped_column(nullable=False, default=0.0)
    latency_ms: Mapped[int] = mapped_column(nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    post: Mapped["Post"] = relationship(back_populates="arbitration", lazy="selectin")
    analyses: Mapped[List["Analysis"]] = relationship(
        back_populates="arbitration", lazy="selectin"
    )
    opportunity: Mapped[Optional["Opportunity"]] = relationship(
        back_populates="arbitration", uselist=False, lazy="selectin"
    )

    __table_args__ = (
        Index("ix_arbitration_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Arbitration(id={self.id}, post_id={self.post_id}, score={self.score})>"


class Opportunity(Base):
    """Validated, ranked business opportunity derived from an Arbitration."""

    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    arbitration_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("arbitrations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Copied from arbitration for fast reads / historical snapshots
    severity: Mapped[int] = mapped_column(nullable=False)
    frequency: Mapped[int] = mapped_column(nullable=False)
    urgency: Mapped[int] = mapped_column(nullable=False)
    monetizability: Mapped[int] = mapped_column(nullable=False)
    score: Mapped[float] = mapped_column(nullable=False, index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    automation_potential: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    status: Mapped[PostStatus] = mapped_column(
        SQLEnum(PostStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=PostStatus.ARBITRATED,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    post: Mapped["Post"] = relationship(back_populates="opportunity", lazy="selectin")
    arbitration: Mapped["Arbitration"] = relationship(
        back_populates="opportunity", lazy="selectin"
    )
    reports: Mapped[List["Report"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_opportunity_score_created", "score", "created_at"),
        Index("ix_opportunity_status_score", "status", "score"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Opportunity(id={self.id}, score={self.score}, status={self.status.value})>"


# ---------------------------------------------------------------------------
# Reporting & delivery
# ---------------------------------------------------------------------------
class Report(Base):
    """Generated report artefact (Markdown + HTML) for an opportunity."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type: Mapped[ReportType] = mapped_column(
        SQLEnum(ReportType, native_enum=False, validate_strings=True),
        nullable=False,
        default=ReportType.AD_HOC,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    extra: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    opportunity: Mapped["Opportunity"] = relationship(
        back_populates="reports", lazy="selectin"
    )
    deliveries: Mapped[List["Delivery"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_report_type_created", "report_type", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Report(id={self.id}, opportunity_id={self.opportunity_id}, type={self.report_type.value})>"


class Delivery(Base):
    """One delivery attempt of a report through a specific channel."""

    __tablename__ = "deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[DeliveryChannel] = mapped_column(
        SQLEnum(DeliveryChannel, native_enum=False, validate_strings=True),
        nullable=False,
        index=True,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        SQLEnum(DeliveryStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=DeliveryStatus.PENDING,
        index=True,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Channel‑specific payload / response (Telegram message_id, SMTP receipt, …)
    metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    report: Mapped["Report"] = relationship(back_populates="deliveries", lazy="selectin")

    __table_args__ = (
        Index("ix_delivery_channel_status", "channel", "status"),
        Index("ix_delivery_sent_created", "sent_at", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Delivery(id={self.id}, channel={self.channel.value}, status={self.status.value})>"


# ---------------------------------------------------------------------------
# Operational observability
# ---------------------------------------------------------------------------
class PipelineRun(Base):
    """Generic, append‑only log of every pipeline stage execution.

    One row per stage per entity (collect, analyse, arbitrate, report, deliver).
    Allows dashboards: success rate, latency percentiles, cost aggregation, …
    """

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Stage identification
    stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # COLLECT, ANALYZE, ARBITRATE, REPORT, DELIVER
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # POST, ANALYSIS, ARBITRATION, REPORT, DELIVERY
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )

    status: Mapped[RunStatus] = mapped_column(
        SQLEnum(RunStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=RunStatus.PENDING,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Cost / resource usage (optional, filled by the stage implementation)
    cost_usd: Mapped[float] = mapped_column(nullable=False, default=0.0)
    tokens_in: Mapped[int] = mapped_column(nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(nullable=False, default=0)

    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    __table_args__ = (
        Index("ix_pipeline_stage_status_started", "stage", "status", "started_at"),
        Index("ix_pipeline_entity", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PipelineRun(id={self.id}, stage={self.stage}, entity={self.entity_type}:{self.entity_id}, status={self.status.value})>"