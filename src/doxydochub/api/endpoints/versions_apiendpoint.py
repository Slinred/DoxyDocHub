import logging
import shutil
import typing
import os
import zipfile
import tempfile

import werkzeug.datastructures
import flask
import flask_restx
import sqlalchemy.exc as sqla_exc

from ...server.server_config import DoxyDocHubConfig
from ...database.database import DoxyDocHubDatabase
from ...database.database_schema import Project, ProjectVersion, ProjectMetadata


class DoxyDocHubApiVersionsEndpoint:

    ENDPOINT = "versions"

    def __init__(
        self,
        api: flask_restx.Api,
        db: DoxyDocHubDatabase,
        server_config: DoxyDocHubConfig,
        config: typing.Optional[dict[typing.Any, typing.Any]] = None,
    ):
        """
        Initialize the versions endpoint.
        :param api: Instance of flask_restx.flask_restx.Api
        :param db: Instance of DoxyDocHubDatabase
        :param server_config: Instance of DoxyDocHubConfig
        :param config: Optional config dict
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        ns: flask_restx.Namespace = api.namespace(
            self.ENDPOINT, description="Project version related operations"
        )

        new_version_model = ns.model(
            "NewVersion",
            {
                "project_id": flask_restx.fields.String(
                    required=True,
                    description="ID of the project this version belongs to",
                ),
                "version": flask_restx.fields.String(
                    required=True, description="Version string"
                ),
            },
        )

        existing_version_model = ns.model(
            "ExistingVersion",
            {
                "id": flask_restx.fields.String(
                    required=False, description="Unique ID of the version"
                ),
                "version": flask_restx.fields.String(
                    required=False, description="Version string"
                ),
                "project_id": flask_restx.fields.String(
                    required=False,
                    description="ID of the project this version belongs to",
                ),
                "created_at": flask_restx.fields.String(
                    required=False, description="Creation timestamp"
                ),
                "storage_path": flask_restx.fields.String(
                    required=False,
                    description="Path where the documentation files are stored on the server",
                ),
            },
        )
        upload_parser = flask_restx.reqparse.RequestParser()
        upload_parser.add_argument(
            "file",
            location="files",
            type=werkzeug.datastructures.FileStorage,
            required=True,
        )

        @ns.route("/")
        class Versions(flask_restx.Resource):  # type: ignore
            """Handles version objects related to projects"""

            @ns.doc("versions_info")
            @ns.response(200, "Success")
            def get(inner_self) -> dict[str, typing.Any] | tuple[list[typing.Any], int]:
                """Returns all version objects"""
                try:
                    versions = db.session.query(ProjectVersion).all()
                    return [v.to_dict() for v in versions], 200
                except sqla_exc.SQLAlchemyError as e:
                    logging.error(f"Database error: {e}")
                    return {"error": "Database error"}, 500

            @ns.doc("create_version")
            @ns.response(201, "Version created", existing_version_model)
            @ns.response(400, "Invalid input")
            @ns.response(404, "Project not found")
            @ns.response(500, "Internal server error")
            @ns.expect(new_version_model, validate=True)
            def post(
                inner_self,
            ) -> dict[str, typing.Any] | tuple[dict[str, typing.Any], int]:
                """Creates a new version for a project"""
                try:
                    data: dict[str, typing.Optional[typing.Any]] = flask.request.json
                    project_id = data.get("project_id")
                    version_str = data.get("version")

                    project = db.session.query(Project).filter_by(id=project_id).first()
                    if not project:
                        return {"error": "Project not found"}, 404

                    # ensure this project does not already contain this version
                    version = (
                        db.session.query(ProjectVersion)
                        .filter_by(version=version_str, project_id=project_id)
                        .first()
                    )
                    if version:
                        return {
                            "error": f"Version {version_str} already exists for this project! Please update via PUT if you want to modify that version!",
                            "version": version.to_dict(),
                        }, 400

                    new_version = ProjectVersion(
                        version=version_str,
                        project_id=project_id,
                    )
                    db.session.add(new_version)
                    db.session.flush()  # To get the new_version.id
                    storage_path: str = server_config.data.data_dir
                    storage_path = os.path.abspath(
                        os.path.join(storage_path, str(project.id), str(new_version.id))
                    )
                    os.makedirs(storage_path, exist_ok=True)
                    new_version.storage_path = storage_path
                    db.session.commit()
                    return new_version.to_dict(), 201
                except sqla_exc.SQLAlchemyError as e:
                    logging.error(f"Database error: {e}")
                    return {"error": "Database error"}, 500

        @ns.route("/<string:version_id>")
        class VersionByID(flask_restx.Resource):  # type: ignore
            """Handles single version object by ID"""

            @ns.doc("get_version")
            @ns.response(200, "Success", new_version_model)
            @ns.response(404, "Version not found")
            @ns.response(500, "Internal server error")
            def get(
                inner_self, version_id: str
            ) -> dict[str, typing.Any] | tuple[dict[str, typing.Any], int]:
                """Returns a version object by ID"""
                try:
                    version = (
                        db.session.query(ProjectVersion)
                        .filter_by(id=version_id)
                        .first()
                    )
                    if not version:
                        return {"error": "Version not found"}, 404
                    return version.to_dict(), 200
                except sqla_exc.SQLAlchemyError as e:
                    logging.error(f"Database error: {e}")
                    return {"error": "Database error"}, 500

        @ns.route("/<string:version_id>/data")
        class VersionData(flask_restx.Resource):  # type: ignore
            """Handles version data retrieval"""

            @ns.doc("get_version_data")
            @ns.response(200, "Success")
            @ns.response(404, "No data available")
            @ns.response(500, "Internal server error")
            def get(
                inner_self, version_id: str
            ) -> dict[str, typing.Any] | tuple[dict[str, typing.Any], int]:
                """Returns the doxygen-generated HTML documentation files as a ZIP archive for the specified version"""
                try:
                    version = (
                        db.session.query(ProjectVersion)
                        .filter_by(id=version_id)
                        .first()
                    )
                    if not version:
                        return {"error": "Version not found"}, 404

                    project = (
                        db.session.query(Project)
                        .filter_by(id=version.project_id)
                        .first()
                    )
                    if not project:
                        return {"error": "Project not found"}, 404

                    if (
                        not version.storage_path
                        or not os.path.exists(version.storage_path)
                        or not os.listdir(version.storage_path)
                    ):
                        return {"error": "No data available"}, 404

                    zip_filename = f"{project.name}_{version.version}_Docs.zip"
                    zip_path = os.path.join(tempfile.gettempdir(), zip_filename)

                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                        for root, _, files in os.walk(str(version.storage_path)):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(
                                    file_path, version.storage_path
                                )
                                zipf.write(file_path, arcname)

                    return flask.send_file(
                        zip_path,
                        mimetype="application/zip",
                        as_attachment=True,
                        download_name=zip_filename,
                    )
                except sqla_exc.SQLAlchemyError as e:
                    logging.error(f"Database error: {e}")
                    return {"error": "Database error"}, 500

            @ns.doc("upload_version_data")
            @ns.response(201, "Version data uploaded")
            @ns.response(400, "Invalid input")
            @ns.response(403, "Data already exists for this version")
            @ns.response(404, "Version not found")
            @ns.response(500, "Internal server error")
            @ns.expect(upload_parser, validate=True)
            def post(
                inner_self, version_id: str
            ) -> dict[str, typing.Any] | tuple[dict[str, typing.Any], int]:
                """Uploads doxygen-generated HTML documentation as .zip archive for the specified version"""
                try:
                    args = upload_parser.parse_args()
                    file = args.get("file")

                    if not file or not isinstance(
                        file, werkzeug.datastructures.FileStorage
                    ):
                        return {"error": "No file provided"}, 400
                    if not file.filename.endswith(".zip"):
                        return {"error": "Uploaded file must be a .zip archive"}, 400

                    version = (
                        db.session.query(ProjectVersion)
                        .filter_by(id=version_id)
                        .first()
                    )
                    if not version:
                        return {"error": "Version not found"}, 404

                    storage_path: str = version.storage_path
                    if not storage_path:
                        return {"error": "Invalid storage path"}, 400
                    if os.path.exists(storage_path) and os.listdir(storage_path):
                        return {"error": "Data already exists for this version"}, 403

                    os.makedirs(storage_path, exist_ok=True)

                    file_path = os.path.join(tempfile.gettempdir(), "upload.zip")
                    file.save(file_path)

                    with zipfile.ZipFile(file_path, "r") as zipf:
                        zipf.extractall(storage_path)
                    os.remove(file_path)

                    if not any(
                        f.lower() == "index.html" for f in os.listdir(storage_path)
                    ):
                        shutil.rmtree(storage_path)
                        return {
                            "error": "Uploaded data must contain an index.html file"
                        }, 400

                    return {"message": "Version data uploaded successfully"}, 201
                except sqla_exc.SQLAlchemyError as e:
                    logging.error(f"Database error: {e}")
                    return {"error": "Database error"}, 500

        api.add_namespace(ns, path=f"/{self.ENDPOINT}")
