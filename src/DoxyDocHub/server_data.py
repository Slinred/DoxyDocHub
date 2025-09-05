import typing
import os
import json
import logging

class DoxyDocHubProject:
    def __init__(self, name: str, root_project: typing.Optional[str] = None):
        self.name = name
        self.root_project = root_project
        self.versions: list[str] = []

        self.metadata: dict[str, typing.Any] = {}

    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "name": self.name,
            "root_project": self.root_project if self.root_project else None,
            "versions": self.versions,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, typing.Any]) -> 'DoxyDocHubProject':
        proj = cls(data["name"], data["root_project"])
        proj.versions = data.get("versions", [])
        proj.metadata = data.get("metadata", {})
        return proj

class DoxyDocHubData:

    DATABASE_FILE = "doxydoc_db.json"

    def __init__(self, data_dir: str):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._projects: list[DoxyDocHubProject] = []
        self._db_file = os.path.abspath(os.path.join(data_dir, self.DATABASE_FILE))

    def load(self):
        data_dir = os.path.dirname(self._db_file)
        self._logger.info(f"Loading data from {self._db_file}...")

        if not os.path.exists(data_dir) or not os.path.isdir(data_dir):
            raise FileNotFoundError(f"Data directory '{data_dir}' does not exist or is not a directory!")

        if not os.path.exists(self._db_file):
            self._logger.warning(f"Database file '{self._db_file}' not found. Starting with empty data.")
            self.save()
            return
        
        with open(self._db_file, 'r') as f:
            data = json.load(f)
            self._projects = []
            for proj_data in data:
                self._projects.append(DoxyDocHubProject.from_dict(proj_data))
        
    def save(self):
        data_dir = os.path.dirname(self._db_file)
        if not os.path.exists(data_dir) or not os.path.isdir(data_dir):
            raise FileNotFoundError(f"Data directory '{data_dir}' does not exist or is not a directory!")

        with open(self._db_file, 'w') as f:
            json.dump([p.to_dict() for p in self._projects], f, indent=4)
