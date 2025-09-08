import logging
import typing

import flask_restx
import flask

import sqlalchemy.exc as sqla_exc

from ...database.database import DoxyDocHubDatabase
from ...database.database_schema import Project, ProjectVersion, ProjectMetadata


class DoxyDocHubApiProjectsEndpoint:

    ENDPOINT = "projects"

    def __init__(
        self,
        api: flask_restx.Api,
        db: DoxyDocHubDatabase,
        config: typing.Optional[dict[typing.Any, typing.Any]] = None,
    ):
        """
        Initialize the Projects endpoint.
        :param api: Instance of flask_restx.flask_restx.Api
        :param db: Instance of DoxyDocHubDatabase
        :param config: Optional config dict
        """
        self.db = db
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        ns: flask_restx.Namespace = api.namespace(
            self.ENDPOINT, description="Project operations"
        )

        new_project_model = ns.model(
            "NewProject",
            {
                "name": flask_restx.fields.String(
                    required=True, description="Project name"
                ),
                "origin_url": flask_restx.fields.String(
                    required=True,
                    description="Origin URL (where the docs are generated from)",
                ),
                "parent_id": flask_restx.fields.String(
                    required=False, description="Optional parent project ID"
                ),
                "metadata": flask_restx.fields.Raw(
                    required=False, description="Optional key-value metadata"
                ),
            },
        )

        existing_project_model = ns.model(
            "ExistingProject",
            {
                "id": flask_restx.fields.String(
                    required=True, description="Project ID (UUIDv4)"
                ),
                "name": flask_restx.fields.String(
                    required=False, description="Project name", default=None
                ),
                "origin_url": flask_restx.fields.String(
                    required=False,
                    default=None,
                    description="Origin URL (where the docs are generated from)",
                ),
                "parent_id": flask_restx.fields.String(
                    required=False,
                    default=None,
                    description="Optional parent project ID",
                ),
                "metadata": flask_restx.fields.Raw(
                    required=False,
                    default=None,
                    description="Optional key-value metadata",
                ),
                "latest_version_id": flask_restx.fields.String(
                    required=False,
                    default=None,
                    description="Latest version (must be an existing project's version id if provided)",
                ),
            },
        )

        project_id_model = ns.model(
            "ProjectID",
            {
                "id": flask_restx.fields.String(
                    required=True, description="Project ID (UUIDv4)"
                )
            },
        )

        @ns.route("/")
        class Projects(flask_restx.Resource):  # type: ignore
            """Shows a list of all projects, and lets you POST to add new projects, PUT to update existing ones and DELETE to remove existing ones."""

            @ns.doc("list_projects")
            def get(inner_self) -> list[dict[str, typing.Any]]:
                """List all projects with metadata"""
                projects = self.db.session.query(Project).all()
                return [p.to_dict() for p in projects]

            @ns.doc("create_project")
            @ns.response(201, "Project created successfully")
            @ns.response(409, "Project with this name already exists")
            @ns.response(400, "Invalid input")
            @ns.response(500, "Internal server error")
            @ns.expect(new_project_model, validate=True)
            def post(inner_self) -> tuple[dict[str, typing.Any], int]:
                """Create a new project if it does not exist yet"""

                data: dict[str, typing.Any] = flask.request.get_json()
                name = data.get("name")
                origin_url = data.get("origin_url")
                parent_id = data.get("parent_id")
                metadata = data.get("metadata", {})

                # Check if project with the same name already exists
                existing = db.session.query(Project).filter_by(name=name).first()
                if existing:
                    ErrorMsg = f"Project with name '{name}' already exists. Specify a different name!"
                    self.logger.warning(ErrorMsg)
                    return (
                        {
                            "error": ErrorMsg,
                            "id": str(existing.id),
                        },
                        409,
                    )

                try:
                    # Create project
                    project = Project(
                        name=name, origin_url=origin_url, parent_id=parent_id
                    )
                    db.session.add(project)
                    db.session.flush()  # flush to get project.id

                    # Add optional metadata
                    for key, value in metadata.items():
                        db.session.add(
                            ProjectMetadata(project_id=project.id, key=key, value=value)
                        )

                    db.session.commit()
                    self.logger.info(f"Created project {project.name} ({project.id})")
                    return (
                        project.to_dict(),
                        201,
                    )

                except sqla_exc.SQLAlchemyError as e:
                    db.session.rollback()
                    self.logger.exception("Failed to create project")
                    return {"error": "Database error", "details": str(e)}, 500

            @ns.doc("update_project")
            @ns.response(200, "Project updated successfully")
            @ns.response(201, "New project created successfully")
            @ns.response(400, "Invalid input")
            @ns.response(500, "Internal server error")
            @ns.expect(existing_project_model, validate=True)
            def put(inner_self) -> tuple[dict[str, typing.Any], int]:
                """Update existing project or creates if not existing"""

                data: dict[str, typing.Any] = flask.request.get_json()

                id = data.get("id")
                name = data.get("name")
                origin_url = data.get("origin_url")
                parent_id = data.get("parent_id")
                metadata = data.get("metadata", {})
                latest_version_id = data.get("latest_version_id")

                try:
                    result = 200
                    project = db.session.query(Project).filter_by(id=id).first()
                    if not project:
                        self.logger.info(
                            f"Project with ID {id} not found, creating new one"
                        )
                        # Create new project
                        project = Project(
                            id=id,
                            name=name,
                            origin_url=origin_url,
                            parent_id=parent_id,
                            latest_version_id=latest_version_id,
                        )
                        db.session.add(project)
                        db.session.flush()
                        result = 201
                    else:
                        project.name = name if name is not None else project.name
                        project.origin_url = (
                            origin_url if origin_url is not None else project.origin_url
                        )
                        project.parent_id = (
                            parent_id if parent_id is not None else project.parent_id
                        )
                        project.latest_version_id = (
                            latest_version_id
                            if latest_version_id is not None
                            else project.latest_version_id
                        )
                        result = 200

                    project.update_metadata(metadata)
                    db.session.commit()
                    self.logger.info(f"Updated project {project.name} ({project.id})")
                    return (
                        project.to_dict(),
                        result,
                    )
                except sqla_exc.SQLAlchemyError as e:
                    db.session.rollback()
                    self.logger.exception("Failed to update project")
                    return {"error": "Database error", "details": str(e)}, 500

            @ns.doc("delete_project")
            @ns.response(200, "Project deleted successfully")
            @ns.response(400, "Invalid input")
            @ns.response(404, "Project not found")
            @ns.response(500, "Internal server error")
            @ns.expect(project_id_model, validate=True)
            def delete(inner_self) -> tuple[dict[str, typing.Any], int]:
                """Deletes an existing project"""
                data: dict[str, typing.Any] = flask.request.get_json()

                id = data.get("id")

                try:
                    project = db.session.query(Project).filter_by(id=id).first()
                    if not project:
                        self.logger.info(
                            f"Project with ID {id} not found! Cannot delete."
                        )
                        return {"error": "Project not found"}, 404
                    project_name = project.name
                    # Delete the project
                    db.session.delete(project)
                    # Also delete all associated versions and metadata
                    db.session.query(ProjectVersion).filter_by(project_id=id).delete()
                    db.session.query(ProjectMetadata).filter_by(project_id=id).delete()
                    # Also set parent to null for projects that have this project as parent
                    children = db.session.query(Project).filter_by(parent_id=id)
                    for child in children:
                        child.parent_id = None
                    db.session.commit()
                    self.logger.info(f"Deleted project {project_name} ({id})")
                    return (
                        {},
                        200,
                    )
                except sqla_exc.SQLAlchemyError as e:
                    db.session.rollback()
                    self.logger.exception("Failed to update project")
                    return {"error": "Database error", "details": str(e)}, 500

        @ns.route("/tree")
        class ProjectTree(flask_restx.Resource):  # type: ignore
            """Shows the project tree structure."""

            @ns.doc("get_project_tree")
            @ns.response(200, "Success")
            @ns.response(500, "Internal server error")
            def get(inner_self) -> list[dict[str, typing.Any]]:
                """Get the project tree structure"""
                projects = self.db.session.query(Project).all()

                def build_tree(proj: Project) -> dict[str, typing.Any]:
                    return {
                        "id": str(proj.id),
                        "name": proj.name,
                        "origin_url": proj.origin_url,
                        "metadata": {
                            item.key: item.value for item in proj.metadata_items
                        },
                        "children": [build_tree(child) for child in proj.children],
                    }

                # Find root projects (those without a parent)
                root_projects = [p for p in projects if p.parent_id is None]
                tree = [build_tree(p) for p in root_projects]
                return tree

        api.add_namespace(ns, path=f"/{self.ENDPOINT}")
