import uuid
from datetime import datetime, timezone
import typing
import os

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    TypeDecorator,
    Dialect,
    event,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, declarative_base
import slugify

DataBaseSchema = declarative_base()


# Custom GUID type for cross-database compatibility
class GUID(TypeDecorator[str]):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise stores as string.
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: typing.Optional[typing.Any], dialect: Dialect):
        if value is None or value == "":
            return None
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
    name = Column(String(255), nullable=False, unique=True)
    name_slug = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    origin_url = Column(Text, nullable=False)
    latest_version_id = Column(
        GUID(),
        ForeignKey("project_versions.id", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )

    parent_id = Column(GUID(), ForeignKey("projects.id"), nullable=True)  # type: ignore

    parent = relationship("Project", remote_side=[id], back_populates="children")
    children = relationship("Project", back_populates="parent", cascade="all, delete")

    versions = relationship(
        "ProjectVersion",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="[ProjectVersion.project_id]",
    )

    latest_version = relationship(
        "ProjectVersion", foreign_keys=[latest_version_id], post_update=True
    )

    metadata_items = relationship(
        "ProjectMetadata", back_populates="project", cascade="all, delete-orphan"
    )

    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.name_slug = slugify.slugify(self.name, lowercase=False)

    def update_metadata(self, new_metadata: dict[str, str]) -> None:
        existing_keys = {item.key: item for item in self.metadata_items}
        for key, value in new_metadata.items():
            if key in existing_keys:
                existing_keys[key].value = value
            else:
                self.metadata_items.append(
                    ProjectMetadata(project_id=self.id, key=key, value=value)
                )

        # Remove metadata items not in new_metadata
        for key in list(existing_keys.keys()):
            if key not in new_metadata:
                self.metadata_items.remove(existing_keys[key])

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "name_slug": self.name_slug,
            "created_at": self.created_at.isoformat(),
            "origin_url": self.origin_url,
            "latest_version": (
                self.latest_version.version if self.latest_version else None
            ),
            "parent": self.parent.id if self.parent else None,
            "children": [child.id for child in self.children],
            "versions": [v.to_dict() for v in self.versions],
            "metadata": {item.key: item.value for item in self.metadata_items},
        }


class ProjectVersion(DataBaseSchema):
    __tablename__ = "project_versions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)  # type: ignore
    version = Column(String(255), nullable=False, unique=False)
    version_slug = Column(String(255), nullable=False, unique=False)
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)  # type: ignore
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    storage_path = Column(Text, nullable=True)

    project = relationship(
        "Project", back_populates="versions", foreign_keys=[project_id]
    )

    def __init__(self, version, **kwargs):
        super().__init__(**kwargs)
        self.version = version
        self.version_slug = slugify.slugify(self.version, lowercase=False)

    def has_docs(self) -> bool:
        if self.storage_path:
            index_path = os.path.join(self.storage_path, "index.html")
            return os.path.exists(index_path)
        return False

    def to_dict(self) -> dict[str, typing.Any]:

        return {
            "id": str(self.id),
            "version": self.version,
            "version_slug": self.version_slug,
            "created_at": self.created_at.isoformat(),
            "storage_path": self.storage_path,
            "project_id": str(self.project_id),
            "has_docs": self.has_docs(),
        }


class ProjectMetadata(DataBaseSchema):
    __tablename__ = "project_metadata"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)  # type: ignore
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)  # type: ignore
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)

    project = relationship("Project", back_populates="metadata_items")

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "key": self.key,
            "value": self.value,
        }


# after insert on ProjectVersion, update the project's latest_version_id
@event.listens_for(ProjectVersion, "after_insert")
def update_latest_version(mapper, connection, target):
    # target = newly inserted ProjectVersion
    # update the Project.latest_version_id
    connection.execute(
        Project.__table__.update()
        .where(Project.id == target.project_id)
        .values(latest_version_id=target.id)
    )
