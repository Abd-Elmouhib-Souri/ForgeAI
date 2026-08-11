import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    ForeignKey,
    DateTime,
    Enum as SQLEnum,
    Float,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    ENTREPRENEUR = "entrepreneur"
    STUDENT = "student"
    CONSULTANT = "consultant"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    google_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum"),
        default=UserRole.ENTREPRENEUR,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    email_verification_token_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    email_verification_expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    password_reset_token_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    password_reset_expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    two_factor_secret: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    industry: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    market_region: Mapped[str] = mapped_column(
        String(100),
        default="Tunisie",
        nullable=False,
    )

    # Language Lock.
    # fr = rapport et agents en français.
    # en = rapport et agents en anglais.
    output_language: Mapped[str] = mapped_column(
        String(10),
        default="fr",
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="ideation",
        nullable=False,
    )

    startup_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    analysis_status: Mapped[str] = mapped_column(
        String(50),
        default="not_started",
        nullable=False,
    )

    analysis_step: Mapped[str] = mapped_column(
        String(100),
        default="idle",
        nullable=False,
    )

    analysis_progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    analysis_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    analysis_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    analysis_started_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    analysis_completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    analysis_run_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )

    analysis_heartbeat_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    analysis_attempt: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="projects",
    )

    versions: Mapped[List["ProjectVersion"]] = relationship(
        "ProjectVersion",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    exports: Mapped[List["Export"]] = relationship(
        "Export",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    snapshot_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    change_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="versions",
    )


class ExportFormat(str, Enum):
    PDF = "pdf"
    WORD = "word"
    POWERPOINT = "powerpoint"


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    format: Mapped[ExportFormat] = mapped_column(
        SQLEnum(ExportFormat, name="export_format_enum"),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    template_used: Mapped[str] = mapped_column(
        String(50),
        default="business",
        nullable=False,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="exports",
    )