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
from ...database.database_schema import (
    DocumentedProject,
    DocumentedVersion,
    MetadataDbObject,
)


class DoxyDocHubApiVersionsEndpoint:

    ENDPOINT = "doc_versions"

    def __init__(
        self,
        api: flask_restx.Api,
        db: DoxyDocHubDatabase,
        server_config: DoxyDocHubConfig,
        config: typing.Optional[dict[typing.Any, typing.Any]] = None,
    ):
        """
        Initialize the doc_versions endpoint.
        :param api: Instance of flask_restx.flask_restx.Api
        :param db: Instance of DoxyDocHubDatabase
        :param server_config: Instance of DoxyDocHubConfig
        :param config: Optional config dict
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        ns: flask_restx.Namespace = api.namespace(
            self.ENDPOINT,
            description="Document access for a DocumentedProject",
        )

        new_docversion_model = ns.model(
            "NewDocVersion",
            {
                "project_id": flask_restx.fields.String(
                    required=True,
                    description="ID of the project this version belongs to",
                ),
                "version": flask_restx.fields.String(
                    required=True, description="Version string"
                ),
                "metadata": flask_restx.fields.Nested(
                    ns.model("Metadata", {}),
                    required=False,
                    description="Optional metadata for the version (JSON object)",
                ),
            },
        )

        existing_docversion_model = ns.model(
            "ExistingDocVersion",
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
                "metadata": flask_restx.fields.Nested(
                    ns.model("Metadata", {}),
                    required=False,
                    description="Optional metadata for the version (JSON object)",
                ),
            },
        )

        create_docversion_parser = flask_restx.reqparse.RequestParser()
        create_docversion_parser.add_argument(
            "version", type=str, location="form", required=True
        )
        create_docversion_parser.add_argument(
            "project_id", type=str, location="form", required=True
        )
        create_docversion_parser.add_argument(
            "docs_archive",
            type=werkzeug.datastructures.FileStorage,
            location="files",
            required=True,
        )
        create_docversion_parser.add_argument(
            "metadata",
            type=str,
            location="form",
            required=False,
            help="Optional metadata for the version (JSON object)",
        )

        update_docversion_parser = flask_restx.reqparse.RequestParser()
        update_docversion_parser.add_argument(
            "version", type=str, location="form", required=False
        )
        update_docversion_parser.add_argument(
            "project_id", type=str, location="form", required=False
        )
        update_docversion_parser.add_argument(
            "docs_archive",
            type=werkzeug.datastructures.FileStorage,
            location="files",
            required=False,
        )
        update_docversion_parser.add_argument(
            "metadata",
            type=str,
            location="form",
            required=False,
            help="Optional metadata for the version (JSON object). Already existing keys will be updated, new will be added",
        )

        @ns.route("/")
        class DocVersions(flask_restx.Resource):  # type: ignore
            """Handles DocumentedVersion objects related to DocumentedProjects"""

            @ns.doc("docversions_info")
            @ns.response(200, "Success")
            def get(inner_self) -> dict[str, typing.Any] | tuple[list[typing.Any], int]:
                """Returns all version objects"""
                try:
                    doc_versions = db.session.query(DocumentedVersion).all()
                    return [v.to_dict(db.session) for v in doc_versions], 200
                except sqla_exc.SQLAlchemyError as e:
                    logging.error(f"Database error: {e}")
                    return {"error": "Database error"}, 500

            @ns.doc("create_version")
            @ns.response(201, "DocumentedVersion created", existing_docversion_model)
            @ns.response(400, "Invalid input")
            @ns.response(404, "DocumentedProject not found")
            @ns.response(500, "Internal server error")
            @ns.expect(create_docversion_parser, validate=True)
            def post(
                inner_self,
            ) -> dict[str, typing.Any] | tuple[dict[str, typing.Any], int]:
                """Creates a new version for a project"""
                try:
                    args = create_docversion_parser.parse_args()
                    project_id: str = args.get("project_id")
                    version_str: str = args.get("version")
                    docs_archive: werkzeug.datastructures.FileStorage = args.get(
                        "docs_archive"
                    )

                    project = (
                        db.session.query(DocumentedProject)
                        .filter_by(id=project_id)
                        .first()
                    )
                    if not project:
                        return {"error": "DocumentedProject not found"}, 404

                    # ensure this project does not already contain this version
                    version = (
                        db.session.query(DocumentedVersion)
                        .filter_by(version=version_str, project_id=project_id)
                        .first()
                    )
                    if version:
                        return {
                            "error": f"Version {version_str} already exists for this project! Please update via version specifc PUT if you want to modify that version!",
                            "version": version.to_dict(),
                        }, 400

                    new_version = DocumentedVersion(
                        version=version_str,
                        project_id=project_id,
                    )
                    db.session.add(new_version)
                    db.session.flush()  # To get the new_version.id
                    new_version.storage_path = os.path.abspath(
                        os.path.join(
                            server_config.data.data_dir,
                            str(project.id),
                            str(new_version.id),
                        )
                    )
                    db.session.commit()

                    error, result = self._process_doc_archive(
                        new_version, docs_archive, False
                    )
                    if result != 201:
                        db.session.delete(new_version)
                        db.session.commit()
                        return error, result

                    return new_version.to_dict(db.session), 201
                except sqla_exc.SQLAlchemyError as e:
                    logging.error(f"Database error: {e}")
                    return {"error": "Database error"}, 500

        @ns.route("/<string:doc_version_id>")
        class DocVersionByID(flask_restx.Resource):  # type: ignore
            """Handles single DocumentedVersion object by ID"""

            @ns.doc("get_docversion")
            @ns.response(200, "Success", new_docversion_model)
            @ns.response(404, "DocumentedVersion not found")
            @ns.response(500, "Internal server error")
            def get(
                inner_self, doc_version_id: str
            ) -> dict[str, typing.Any] | tuple[dict[str, typing.Any], int]:
                """Returns a DocumentedVersion object by ID"""
                try:
                    doc_version = (
                        db.session.query(DocumentedVersion)
                        .filter_by(id=doc_version_id)
                        .first()
                    )
                    if not doc_version:
                        return {"error": "DocumentedVersion not found"}, 404
                    return doc_version.to_dict(), 200
                except sqla_exc.SQLAlchemyError as e:
                    logging.error(f"Database error: {e}")
                    return {"error": "Database error"}, 500

            @ns.doc("update_docversion")
            @ns.response(200, "DocumentedVersion updated", existing_docversion_model)
            @ns.response(400, "Invalid input")
            @ns.response(404, "DocumentedVersion not found")
            @ns.response(500, "Internal server error")
            @ns.expect(update_docversion_parser, validate=True)
            def put(
                inner_self, doc_version_id: str
            ) -> dict[str, typing.Any] | tuple[dict[str, typing.Any], int]:
                """Updates a version object by ID"""
                try:
                    args = update_docversion_parser.parse_args()
                    version_str: typing.Optional[str] = args.get("version")
                    project_id: typing.Optional[str] = args.get("project_id")
                    docs_archive: typing.Optional[
                        werkzeug.datastructures.FileStorage
                    ] = args.get("docs_archive")

                    version = (
                        db.session.query(DocumentedVersion)
                        .filter_by(id=doc_version_id)
                        .first()
                    )
                    if not version:
                        return {"error": "Version not found"}, 404

                    if project_id:
                        project = (
                            db.session.query(DocumentedProject)
                            .filter_by(id=project_id)
                            .first()
                        )
                        if not project:
                            return {"error": "DocumentedProject not found"}, 404
                        version.project_id = project_id

                    if version_str:
                        version.version = version_str

                    if docs_archive:
                        error, result = self._process_doc_archive(
                            version, docs_archive, True
                        )
                        if result != 201:
                            db.session.rollback()
                            return error, result

                    db.session.commit()
                    return version.to_dict(), 200
                except sqla_exc.SQLAlchemyError as e:
                    logging.error(f"Database error: {e}")
                    return {"error": "Database error"}, 500

        @ns.route("/<string:doc_version_id>/data")
        class VersionData(flask_restx.Resource):  # type: ignore
            """Handles version data retrieval"""

            @ns.doc("get_version_data")
            @ns.response(200, "Success")
            @ns.response(404, "No data available")
            @ns.response(500, "Internal server error")
            def get(
                inner_self, doc_version_id: str
            ) -> dict[str, typing.Any] | tuple[dict[str, typing.Any], int]:
                """Returns the doxygen-generated HTML documentation files as a ZIP archive for the specified version"""
                try:
                    version = (
                        db.session.query(DocumentedVersion)
                        .filter_by(id=doc_version_id)
                        .first()
                    )
                    if not version:
                        return {"error": "Version not found"}, 404

                    project = (
                        db.session.query(DocumentedProject)
                        .filter_by(id=version.project_id)
                        .first()
                    )
                    if not project:
                        return {"error": "DocumentedProject not found"}, 404

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

        api.add_namespace(ns, path=f"/{self.ENDPOINT}")

    def _process_doc_archive(
        self,
        version: DocumentedVersion,
        docs_archive: werkzeug.datastructures.FileStorage,
        overwrite: bool = False,
    ) -> tuple[dict[str, str], int]:
        if not docs_archive or not isinstance(
            docs_archive, werkzeug.datastructures.FileStorage
        ):
            return {"error": "No file provided"}, 400
        if not docs_archive.filename.endswith(".zip"):
            return {"error": "Uploaded file must be a .zip archive"}, 400

        if not version:
            return {"error": "Version not found"}, 404

        storage_path: str = version.storage_path
        if not storage_path:
            return {"error": "Invalid storage path"}, 400

        if not overwrite and os.path.exists(storage_path) and os.listdir(storage_path):
            return {"error": "Data already exists for this version"}, 403

        temp_extract_path = os.path.join(tempfile.gettempdir(), "content")
        shutil.rmtree(temp_extract_path, ignore_errors=True)
        os.makedirs(temp_extract_path, exist_ok=True)

        file_path = os.path.join(tempfile.gettempdir(), "upload.zip")
        docs_archive.save(file_path)

        with zipfile.ZipFile(file_path, "r") as zipf:
            zipf.extractall(temp_extract_path)
        os.remove(file_path)

        if not any(f.lower() == "index.html" for f in os.listdir(temp_extract_path)):
            shutil.rmtree(temp_extract_path)
            return {"error": "Uploaded data must contain an index.html file"}, 400

        shutil.rmtree(storage_path, ignore_errors=True)
        shutil.copytree(temp_extract_path, storage_path)
        shutil.rmtree(temp_extract_path)

        return {"message": "Version data uploaded successfully"}, 201
