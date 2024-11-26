from pathlib import Path
from subprocess import run
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class ResourceBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        root_path = Path(self.root)
        resource_file = root_path / "resources.qrc"
        target_file = root_path / "src" / "pypos" / "resources.py"

        run(
            ["pyside6-rcc", resource_file, "-o", target_file],
            check=True,
        )
