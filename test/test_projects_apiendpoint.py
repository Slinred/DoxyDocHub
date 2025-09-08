import pytest
import os
import uuid

import flask
from flask_restx import Api
import sqlalchemy.exc as sqla_exc

from doxydochub.database.database import DoxyDocHubDatabase
from doxydochub.database.database_schema import Project
from doxydochub.server.server_config import DoxyDocHubConfig
from doxydochub.api.endpoints.projects_apiendpoint import DoxyDocHubApiProjectsEndpoint

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


@pytest.fixture
def create_app():
    app = flask.Flask(__name__)
    api = Api(app)
    db = DoxyDocHubDatabase(TEST_DB_URL)
    DoxyDocHubApiProjectsEndpoint(api, db, config=None)
    return app, db


def test_list_projects_empty(clean_test_db, create_app):
    client = create_app[0].test_client()
    response = client.get("/projects/")
    assert response.status_code == 200
    assert response.json == []


def test_create_project(clean_test_db, create_app):
    client = create_app[0].test_client()
    db = create_app[1]
    data = {
        "name": "TestProj",
        "origin_url": "http://test.url",
        "metadata": {"key1": "value1"},
    }
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    assert db.session.query(Project).filter_by(name="TestProj").first() is not None

    response = client.get("/projects/")
    assert response.status_code == 200
    assert response.json[0]["name"] == "TestProj"
    assert response.json[0]["metadata"] == {"key1": "value1"}


def test_create_duplicate_project(create_app):
    client = create_app[0].test_client()
    data = {"name": "TestProj", "origin_url": "http://test.url"}
    client.post("/projects/", json=data)
    response = client.post("/projects/", json=data)
    assert response.status_code == 409
    assert "already exists" in response.json["error"]


def test_create_project_invalid_input(create_app):
    client = create_app[0].test_client()
    # Missing 'name' field
    data = {"origin_url": "http://test.url"}
    response = client.post("/projects/", json=data)
    assert response.status_code == 400
    assert "Input payload validation failed" in response.json["message"]

    # 'name' field is not a string
    data = {"name": 123, "origin_url": "http://test.url"}
    response = client.post("/projects/", json=data)
    assert response.status_code == 400
    assert "Input payload validation failed" in response.json["message"]


def test_create_project_sql_error(monkeypatch, clean_test_db, create_app):
    client = create_app[0].test_client()
    db = create_app[1]

    # Simulate SQLAlchemy error on commit
    def raise_sqlalchemy_error(*args, **kwargs):
        raise sqla_exc.SQLAlchemyError("Simulated DB error")

    monkeypatch.setattr(db.session, "commit", raise_sqlalchemy_error)

    data = {"name": "TestProj", "origin_url": "http://test.url"}
    response = client.post("/projects/", json=data)
    assert response.status_code == 500
    assert "Database error" in response.json["error"]

    # Verify that project was not created
    assert db.session.query(Project).filter_by(name="TestProj").first() is None


def test_update_project(clean_test_db, create_app):
    client = create_app[0].test_client()
    db = create_app[1]
    data = {"name": "TestProj", "origin_url": "http://test.url"}
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    project_id = response.json["id"]

    # Update project
    update_data = {
        "id": project_id,
        "name": "UpdatedProj",
        "origin_url": "http://updated.url",
        "metadata": {"key1": "value1", "key2": "value2"},
    }
    response = client.put(f"/projects/", json=update_data)
    assert response.status_code == 200
    assert response.json["name"] == "UpdatedProj"
    assert response.json["origin_url"] == "http://updated.url"
    assert response.json["metadata"] == {"key1": "value1", "key2": "value2"}

    # Update project
    update_data = {
        "id": project_id,
        "metadata": {"key2": "newvalue2", "key3": "newvalue3"},
    }
    response = client.put(f"/projects/", json=update_data)
    assert response.status_code == 200
    assert response.json["name"] == "UpdatedProj"
    assert response.json["origin_url"] == "http://updated.url"
    assert response.json["metadata"] == {"key2": "newvalue2", "key3": "newvalue3"}

    # Verify in DB
    project = db.session.query(Project).filter_by(id=project_id).first()
    assert project is not None
    assert project.name == "UpdatedProj"
    assert project.origin_url == "http://updated.url"


def test_update_nonexistent_project(clean_test_db, create_app):
    client = create_app[0].test_client()
    update_data = {
        "id": uuid.uuid4(),
        "name": "ProjToBeCreated",
        "origin_url": "http://no.url",
        "metadata": {"key1": "value1"},
    }
    response = client.put(f"/projects/", json=update_data)
    assert response.status_code == 201
    assert response.json["name"] == "ProjToBeCreated"
    assert response.json["origin_url"] == "http://no.url"
    assert response.json["metadata"] == {"key1": "value1"}
    assert response.json["parent"] is None


def test_update_project_sql_error(monkeypatch, clean_test_db, create_app):
    client = create_app[0].test_client()
    db = create_app[1]
    data = {"name": "TestProj", "origin_url": "http://test.url"}
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    project_id = response.json["id"]

    # Simulate SQLAlchemy error on commit
    def raise_sqlalchemy_error(*args, **kwargs):
        raise sqla_exc.SQLAlchemyError("Simulated DB error")

    monkeypatch.setattr(db.session, "commit", raise_sqlalchemy_error)

    update_data = {
        "id": project_id,
        "name": "ShouldFail",
        "origin_url": "http://fail.url",
        "metadata": {"key1": "value1"},
    }
    response = client.put(f"/projects/", json=update_data)
    assert response.status_code == 500
    assert "Database error" in response.json["error"]

    # Verify that project was not updated
    project = db.session.query(Project).filter_by(id=project_id).first()
    assert project is not None
    assert project.name == "TestProj"
    assert project.origin_url == "http://test.url"
    assert project.metadata_items == []


def test_delete_project(clean_test_db, create_app):
    client = create_app[0].test_client()
    db = create_app[1]
    data = {"name": "TestProj", "origin_url": "http://test.url"}
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    project_id = response.json["id"]

    data = {
        "name": "ChildTestProj",
        "origin_url": "http://testchild.url",
        "parent_id": project_id,
    }
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    child_project_id = response.json["id"]

    # Delete project
    response = client.delete(f"/projects/", json={"id": project_id})
    assert response.status_code == 200

    # Verify deletion
    project = db.session.query(Project).filter_by(id=project_id).first()
    assert project is None
    child_project = db.session.query(Project).filter_by(id=child_project_id).first()
    assert child_project is not None
    assert child_project.parent_id is None


def test_delete_nonexistent_project(create_app):
    client = create_app[0].test_client()
    response = client.delete(f"/projects/", json={"id": uuid.uuid4()})
    assert response.status_code == 404
    assert "not found" in response.json["error"]


def test_delete_project_sql_error(monkeypatch, clean_test_db, create_app):
    client = create_app[0].test_client()
    db = create_app[1]
    data = {"name": "TestProj", "origin_url": "http://test.url"}
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    project_id = response.json["id"]

    # Simulate SQLAlchemy error on commit
    def raise_sqlalchemy_error(*args, **kwargs):
        raise sqla_exc.SQLAlchemyError("Simulated DB error")

    monkeypatch.setattr(db.session, "commit", raise_sqlalchemy_error)

    response = client.delete(f"/projects/", json={"id": project_id})
    assert response.status_code == 500
    assert "Database error" in response.json["error"]

    # Verify that project was not deleted
    project = db.session.query(Project).filter_by(id=project_id).first()
    assert project is not None


def test_project_tree(clean_test_db, create_app):
    client = create_app[0].test_client()
    data = {"name": "RootProj", "origin_url": "http://root.url"}
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    root_id = response.json["id"]

    data = {
        "name": "ChildProj1",
        "origin_url": "http://child1.url",
        "parent_id": root_id,
    }
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    child1_id = response.json["id"]

    data = {
        "name": "ChildProj2",
        "origin_url": "http://child2.url",
        "parent_id": root_id,
    }
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    child2_id = response.json["id"]

    data = {
        "name": "GrandChildProj",
        "origin_url": "http://grandchild.url",
        "parent_id": child1_id,
    }
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    grandchild_id = response.json["id"]

    data = {"name": "AnotherRootProj", "origin_url": "http://anotherroot.url"}
    response = client.post("/projects/", json=data)
    assert response.status_code == 201
    another_root_id = response.json["id"]

    # Get project tree
    response = client.get("/projects/tree")
    assert response.status_code == 200
    tree = response.json
    assert len(tree) == 2  # Two root projects
    assert tree[0]["id"] == root_id
    assert tree[1]["id"] == another_root_id
    assert len(tree[0]["children"]) == 2
    child_ids = {child["id"] for child in tree[0]["children"]}
    assert child1_id in child_ids
    assert child2_id in child_ids

    for child in tree[0]["children"]:
        if child["id"] == child1_id:
            assert len(child["children"]) == 1
            assert child["children"][0]["id"] == grandchild_id
        else:
            assert len(child["children"]) == 0
