from io import BytesIO
import os
import uuid
import zipfile
import pytest
from unittest.mock import MagicMock, patch

import flask
from flask_restx import Api

from doxydochub.api.endpoints.versions_apiendpoint import DoxyDocHubApiVersionsEndpoint
from doxydochub.database.database import DoxyDocHubDatabase
from doxydochub.database.database_schema import Project, ProjectVersion
from doxydochub.server.server_config import DoxyDocHubConfig


TEST_DB_FILENAME = "test_doxydochub.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_FILENAME}"


@pytest.fixture
def clean_test_db():
    # Remove test DB before and after test
    if os.path.exists(TEST_DB_FILENAME):
        os.remove(TEST_DB_FILENAME)
    yield
    if os.path.exists(TEST_DB_FILENAME):
        os.remove(TEST_DB_FILENAME)
    # Remove backup files
    for fname in os.listdir("."):
        if fname.startswith("doxydochub_backup_") and fname.endswith(".db"):
            os.remove(fname)


class DummyProject:
    def __init__(self, name, origin_url):
        self.id = "dummy-id"
        self.name = name
        self.origin_url = origin_url
        self.parent = None
        self.metadata_items = []

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "origin_url": self.origin_url,
            "parent": None,
            "metadata": {},
        }


class DummyConfig(DoxyDocHubConfig):
    class Data:
        data_dir = "/dummy/data/dir"

    def __init__(self):
        pass

    @property
    def data(self):
        return self.Data()


@pytest.fixture
def create_app():
    app = flask.Flask(__name__)
    api = Api(app)
    db = DoxyDocHubDatabase(TEST_DB_URL)
    DoxyDocHubApiVersionsEndpoint(api, db, DummyConfig(), config=None)
    return app, db


def test_get_versions_empty(clean_test_db, create_app):
    client = create_app[0].test_client()
    response = client.get("/versions/")
    assert response.status_code == 200
    assert response.json == []


def test_get_versions_with_data(clean_test_db, create_app):
    app = create_app[0]
    db = create_app[1]
    # Add dummy data
    project = Project(name="TestProject", origin_url="http://example.com")
    db.session.add(project)
    db.session.commit()

    version1 = ProjectVersion(
        version="1.0", project_id=project.id, storage_path="dummy/path/1.0"
    )
    version2 = ProjectVersion(
        version="2.0", project_id=project.id, storage_path="dummy/path/2.0"
    )
    db.session.add(version1)
    db.session.add(version2)
    db.session.commit()

    client = app.test_client()
    response = client.get("/versions/")
    assert response.status_code == 200
    assert len(response.json) == 2
    versions = {v["version"] for v in response.json}
    assert versions == {"1.0", "2.0"}


def test_create_version_success(clean_test_db, create_app, monkeypatch):
    app = create_app[0]
    db = create_app[1]
    # Add dummy project
    project = Project(name="TestProject", origin_url="http://example.com")
    db.session.add(project)
    db.session.commit()

    monkeypatch.setattr("os.makedirs", lambda path, exist_ok: None)

    client = app.test_client()
    response = client.post(
        "/versions/",
        json={"project_id": str(project.id), "version": "1.0"},
    )
    assert response.status_code == 201
    assert "id" in response.json
    assert response.json["version"] == "1.0"
    assert response.json["project_id"] == str(project.id)


def test_create_version_invalid_project(clean_test_db, create_app):
    app = create_app[0]
    client = app.test_client()
    response = client.post(
        "/versions/",
        json={"project_id": str(uuid.uuid4()), "version": "1.0"},
    )
    assert response.status_code == 404
    assert response.json["error"] == "Project not found"


def test_get_version_by_id_success(clean_test_db, create_app):
    app = create_app[0]
    db = create_app[1]
    # Add dummy data
    project = Project(name="TestProject", origin_url="http://example.com")
    db.session.add(project)
    db.session.commit()

    version = ProjectVersion(
        version="1.0", project_id=project.id, storage_path="dummy/path/1.0"
    )
    db.session.add(version)
    db.session.commit()

    client = app.test_client()
    response = client.get(f"/versions/{version.id}")
    assert response.status_code == 200
    assert response.json["id"] == str(version.id)
    assert response.json["version"] == "1.0"
    assert response.json["project_id"] == str(project.id)


def test_get_version_by_id_not_found(clean_test_db, create_app):
    app = create_app[0]
    client = app.test_client()
    response = client.get(f"/versions/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json["error"] == "Version not found"


def test_get_version_files_success(clean_test_db, create_app, monkeypatch):
    app = create_app[0]
    db = create_app[1]
    # Add dummy data
    project = Project(name="TestProject", origin_url="http://example.com")
    db.session.add(project)
    db.session.commit()

    version = ProjectVersion(
        version="1.0", project_id=project.id, storage_path="dummy/path/1.0"
    )
    db.session.add(version)
    db.session.commit()

    def mock_isfile(path):
        return True

    def mock_listdir(path):
        return ["index.html", "style.css"]

    def mock_abspath(path):
        return path

    def mock_join(*args):
        return "/".join(args)

    def mock_makedirs(path, exist_ok):
        pass

    monkeypatch.setattr("os.path.isfile", mock_isfile)
    monkeypatch.setattr("os.listdir", mock_listdir)
    monkeypatch.setattr("os.path.abspath", mock_abspath)
    monkeypatch.setattr("os.path.join", mock_join)
    monkeypatch.setattr("os.makedirs", mock_makedirs)
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("tempfile.gettempdir", lambda: "/tmp")
    monkeypatch.setattr("zipfile.ZipFile", MagicMock())
    monkeypatch.setattr("zipfile.ZipFile.write", lambda self, file_path, arcname: None)
    monkeypatch.setattr(
        "flask.send_file",
        lambda path, mimetype, as_attachment, download_name: flask.make_response(
            f"Mocked send_file: {download_name}"
        ),
    )

    client = app.test_client()
    response = client.get(f"/versions/{version.id}/data")
    assert response.status_code == 200
    assert response.data.decode().startswith(
        "Mocked send_file: TestProject_1.0_Docs.zip"
    )


def test_get_version_files_version_not_found(clean_test_db, create_app):
    app = create_app[0]
    client = app.test_client()
    response = client.get(f"/versions/{uuid.uuid4()}/data")
    assert response.status_code == 404
    assert response.json["error"] == "Version not found"


def test_get_version_files_project_not_found(clean_test_db, create_app):
    app = create_app[0]
    db = create_app[1]
    # Add dummy version without a valid project
    version = ProjectVersion(
        version="1.0", project_id=uuid.uuid4(), storage_path="dummy/path/1.0"
    )
    db.session.add(version)
    db.session.commit()

    client = app.test_client()
    response = client.get(f"/versions/{version.id}/data")
    assert response.status_code == 404
    assert response.json["error"] == "Project not found"


def test_get_version_files_no_data(clean_test_db, create_app, monkeypatch):
    app = create_app[0]
    db = create_app[1]
    # Add dummy data
    project = Project(name="TestProject", origin_url="http://example.com")
    db.session.add(project)
    db.session.commit()

    version = ProjectVersion(
        version="1.0", project_id=project.id, storage_path="dummy/path/1.0"
    )
    db.session.add(version)
    db.session.commit()

    monkeypatch.setattr("os.path.exists", lambda path: False)

    client = app.test_client()
    response = client.get(f"/versions/{version.id}/data")
    assert response.status_code == 404
    assert response.json["error"] == "No data available"


def test_upload_version_success(clean_test_db, create_app, monkeypatch):
    app = create_app[0]
    db = create_app[1]
    # Add dummy project
    project = Project(name="TestProject", origin_url="http://example.com")
    db.session.add(project)
    db.session.commit()

    version = ProjectVersion(
        version="1.0", project_id=project.id, storage_path="dummy/path/1.0"
    )
    db.session.add(version)
    db.session.commit()

    # Create a dummy zip file in memory
    from io import BytesIO

    dummy_zip = BytesIO()
    with zipfile.ZipFile(dummy_zip, "w") as zf:
        zf.writestr("index.html", "<html><body>Test</body></html>")
    dummy_zip.seek(0)

    monkeypatch.setattr("os.listdir", lambda path: ["index.html"])
    monkeypatch.setattr("os.path.exists", lambda path: False)
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok: None)
    monkeypatch.setattr("zipfile.is_zipfile", lambda file: True)
    monkeypatch.setattr("zipfile.ZipFile", MagicMock())
    monkeypatch.setattr("zipfile.ZipFile.extractall", lambda self, path: None)

    data = {
        "project_id": str(project.id),
        "file": (dummy_zip, "docs.zip"),
    }

    client = app.test_client()
    response = client.post(
        f"/versions/{version.id}/data",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    assert response.json["message"] == "Version data uploaded successfully"


def test_upload_version_invalid_file(clean_test_db, create_app):
    app = create_app[0]
    db = create_app[1]
    # Add dummy project
    project = Project(name="TestProject", origin_url="http://example.com")
    db.session.add(project)
    db.session.commit()

    version = ProjectVersion(
        version="1.0", project_id=project.id, storage_path="dummy/path/1.0"
    )
    db.session.add(version)
    db.session.commit()

    client = app.test_client()
    response = client.post(
        f"/versions/{version.id}/data",
        data={},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_upload_version_not_found(clean_test_db, create_app):
    app = create_app[0]
    client = app.test_client()
    response = client.post(
        f"/versions/{uuid.uuid4()}/data",
        data={"file": (BytesIO(b"dummy data"), "docs.zip")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 404
    assert response.json["error"] == "Version not found"


def test_upload_version_not_zip(clean_test_db, create_app, monkeypatch):
    app = create_app[0]
    db = create_app[1]
    # Add dummy project
    project = Project(name="TestProject", origin_url="http://example.com")
    db.session.add(project)
    db.session.commit()

    version = ProjectVersion(
        version="1.0", project_id=project.id, storage_path="dummy/path/1.0"
    )
    db.session.add(version)
    db.session.commit()

    # Create a non-zip file in memory
    non_zip_file = BytesIO(b"This is not a zip file")

    client = app.test_client()
    response = client.post(
        f"/versions/{version.id}/data",
        data={"file": (non_zip_file, "docs.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.json["error"] == "Uploaded file must be a .zip archive"


def test_upload_version_data_already_exists(clean_test_db, create_app, monkeypatch):
    app = create_app[0]
    db = create_app[1]
    # Add dummy project
    project = Project(name="TestProject", origin_url="http://example.com")
    db.session.add(project)
    db.session.commit()

    version = ProjectVersion(
        version="1.0", project_id=project.id, storage_path="dummy/path/1.0"
    )
    db.session.add(version)
    db.session.commit()

    # Create a dummy zip file in memory
    dummy_zip = BytesIO()
    with zipfile.ZipFile(dummy_zip, "w") as zf:
        zf.writestr("index.html", "<html><body>Test</body></html>")
    dummy_zip.seek(0)

    monkeypatch.setattr("os.listdir", lambda path: ["index.html"])
    monkeypatch.setattr("os.path.exists", lambda path: True)  # Simulate existing data
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok: None)
    monkeypatch.setattr("zipfile.is_zipfile", lambda file: True)
    monkeypatch.setattr("zipfile.ZipFile", MagicMock())
    monkeypatch.setattr("zipfile.ZipFile.extractall", lambda self, path: None)

    data = {
        "project_id": str(project.id),
        "file": (dummy_zip, "docs.zip"),
    }

    client = app.test_client()
    response = client.post(
        f"/versions/{version.id}/data",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 403
    assert response.json["error"] == "Data already exists for this version"
