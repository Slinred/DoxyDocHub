import pytest
import os
import json
from src.DoxyDocHub.server_data import DoxyDocHubData, DoxyDocHubProject

def test_empty_database_creation(tmp_path):
    data_dir = tmp_path / "data"
    os.makedirs(data_dir)
    db = DoxyDocHubData(str(data_dir))
    assert os.path.exists(os.path.join(data_dir, db.DATABASE_FILE)) is False
    db.load()  # Should not raise
    assert os.path.exists(os.path.join(data_dir, db.DATABASE_FILE)) is True
    with open(os.path.join(data_dir, db.DATABASE_FILE)) as f:
        data = json.load(f)
    assert data == []


def test_store_and_load_projects(tmp_path):
    data_dir = tmp_path / "data"
    os.makedirs(data_dir)
    db = DoxyDocHubData(str(data_dir))
    # Add projects
    p1 = DoxyDocHubProject("Project1")
    p1.versions = {"v1": "info1"}
    p1.metadata = {"desc": "Test project"}
    db._projects.append(p1)
    db.save()
    # Clear and reload
    db._projects.clear()
    db.load()
    with open(os.path.join(data_dir, db.DATABASE_FILE)) as f:
        loaded = json.load(f)
    assert isinstance(loaded, list)
    assert loaded[0]["name"] == "Project1"
    assert loaded[0]["versions"] == {"v1": "info1"}
    assert loaded[0]["metadata"] == {"desc": "Test project"}
