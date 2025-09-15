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
from sqlalchemy.orm import relationship, declarative_base, Session, remote
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


class BaseDbObject:
    __abstract__ = True

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)  # type: ignore

    def to_dict(self, *args, **kwargs) -> dict[str, typing.Any]:
        return {"id": self.id}


class MetadataDbObject(BaseDbObject, DataBaseSchema):
    __tablename__ = "objects_metadata"

    parent_id = Column(GUID(), nullable=False)  # type: ignore
    parent_type = Column(String(50), nullable=False)

    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)

    def get_parent(self, session: Session):  # type: ignore
        if self.parent_type == "DocumentedProject":
            return session.query(DocumentedProject).get(self.parent_id)
        elif self.parent_type == "DocumentedVersion":
            return session.query(DocumentedVersion).get(self.parent_id)
        return None

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            **super().to_dict(),
            **{
                "parent_id": str(self.parent_id),
                "parent_type": str(self.parent_type),
                "key": self.key,
                "value": self.value,
            },
        }


class MetadataAwareBaseDbObject(BaseDbObject):
    __abstract__ = True

    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    def get_metadata(self, session: Session):
        return (
            session.query(MetadataDbObject)
            .filter_by(parent_id=self.id, parent_type=self.__class__.__name__)
            .all()
        )

    def update_metadata(self, new_metadata: dict[str, str], session: Session) -> None:
        actual_metadata_items = self.get_metadata(session)
        existing_keys = {item.key: item for item in actual_metadata_items}
        for key, value in new_metadata.items():
            if key in existing_keys:
                existing_keys[key].value = value
            else:
                new_metadata_item = MetadataDbObject(
                    parent_id=self.id,
                    parent_type=self.__class__.__name__,
                    key=key,
                    value=value,
                )
                session.add(new_metadata_item)

        # Remove metadata items not in new_metadata
        for key in list(existing_keys.keys()):
            if key not in new_metadata:
                session.delete(existing_keys[key])

        session.commit()

    def to_dict(self, session: Session) -> dict[str, typing.Any]:
        return {
            **super().to_dict(),
            "created_at": self.created_at.isoformat(),
            "metadata": {item.key: item.value for item in self.get_metadata(session)},
        }


class DocumentedProject(MetadataAwareBaseDbObject, DataBaseSchema):
    __tablename__ = "doc_projects"

    # id = MetadataAwareBaseDbObject.id
    name = Column(String(255), nullable=False, unique=True)
    name_slug = Column(String(255), nullable=False, unique=True)
    origin_url = Column(Text, nullable=False)
    latest_version_id = Column(
        GUID(),
        ForeignKey("doc_versions.id", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )

    parent_id = Column(GUID(), ForeignKey(f"{__tablename__}.id"), nullable=True)  # type: ignore

    versions = relationship(
        "DocumentedVersion",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="[DocumentedVersion.project_id]",
    )

    latest_version = relationship(
        "DocumentedVersion", foreign_keys=[latest_version_id], post_update=True
    )

    def to_dict(self, session: Session) -> dict[str, typing.Any]:
        return {
            **MetadataAwareBaseDbObject.to_dict(self, session),
            **{
                "name": self.name,
                "name_slug": self.name_slug,
                "origin_url": self.origin_url,
                "latest_version": (
                    self.latest_version.version if self.latest_version else None
                ),
                "parent": self.parent.id if self.parent else None,
                "children": [child.id for child in self.children],
                "versions": [v.to_dict(session) for v in self.versions],
            },
        }


DocumentedProject.parent = relationship(
    "DocumentedProject",
    primaryjoin="DocumentedProject.parent_id==DocumentedProject.id",
    remote_side=[remote(DocumentedProject.id)],
    back_populates="children",
)
DocumentedProject.children = relationship(
    "DocumentedProject", back_populates="parent", cascade="all, delete"
)


class DocumentedVersion(MetadataAwareBaseDbObject, DataBaseSchema):
    __tablename__ = "doc_versions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)  # type: ignore
    version = Column(String(255), nullable=False, unique=False)
    version_slug = Column(String(255), nullable=False, unique=False)
    project_id = Column(GUID(), ForeignKey("doc_projects.id"), nullable=False)  # type: ignore
    storage_path = Column(Text, nullable=True)

    project = relationship(
        "DocumentedProject", back_populates="versions", foreign_keys=[project_id]
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

    def to_dict(self, session: Session) -> dict[str, typing.Any]:
        return {
            **MetadataAwareBaseDbObject.to_dict(self, session),
            **{
                "version": self.version,
                "version_slug": self.version_slug,
                "storage_path": self.storage_path,
                "project_id": str(self.project_id),
                "has_docs": self.has_docs(),
            },
        }


@event.listens_for(DocumentedProject.name, "set", retval=False)
def on_name_set(target, value, oldvalue, initiator):
    # This runs whenever DocumentedVersion.version is assigned
    target.name_slug = slugify.slugify(value, lowercase=False)
    return value


# after insert on DocumentedVersion, update the project's latest_version_id
@event.listens_for(DocumentedVersion, "after_insert")
def update_latest_version(mapper, connection, target):
    # target = newly inserted DocumentedVersion
    # update the DocumentedProject.latest_version_id
    connection.execute(
        DocumentedProject.__table__.update()
        .where(DocumentedProject.id == target.project_id)
        .values(latest_version_id=target.id)
    )


@event.listens_for(DocumentedVersion.version, "set", retval=False)
def on_version_set(target, value, oldvalue, initiator):
    # This runs whenever DocumentedVersion.version is assigned
    target.version_slug = slugify.slugify(value, lowercase=False)
    return value
