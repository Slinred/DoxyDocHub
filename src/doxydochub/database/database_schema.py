import uuid
from datetime import datetime, timezone
import typing

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    TypeDecorator,
    Dialect,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, declarative_base

DataBaseSchema = declarative_base()


# Custom GUID type for cross-database compatibility
class GUID(TypeDecorator[str]):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise stores as string.
    """

    impl = String(36)

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: typing.Optional[typing.Any], dialect: Dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(
        self, value: typing.Optional[typing.Any], dialect: Dialect
    ) -> typing.Optional[str]:
        if value is None:
            return value
        return str(uuid.UUID(value))


class Project(DataBaseSchema):
    __tablename__ = "projects"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)  # type: ignore
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    origin_url = Column(Text, nullable=False)

    parent_id = Column(GUID(), ForeignKey("projects.id"), nullable=True)  # type: ignore
    parent = relationship("Project", remote_side=[id], backref="children")  # type: ignore

    versions = relationship(
        "ProjectVersion", back_populates="project", cascade="all, delete-orphan"
    )
    metadata_items = relationship(
        "ProjectMetadata", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectVersion(DataBaseSchema):
    __tablename__ = "project_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)  # type: ignore
    version = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    storage_path = Column(Text, nullable=False)

    project = relationship("Project", back_populates="versions")


class ProjectMetadata(DataBaseSchema):
    __tablename__ = "project_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)  # type: ignore
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)

    project = relationship("Project", back_populates="metadata_items")
