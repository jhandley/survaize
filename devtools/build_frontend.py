import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.config import BuilderConfig
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from typing_extensions import override


class CustomHook(BuildHookInterface[BuilderConfig]):
    """Build the React frontend before the wheel/sdist is created."""

    @override
    def initialize(self, version: str, build_data: dict[str, Any]):  # type: ignore[any]
        root = Path(__file__).resolve().parent.parent
        frontend = root / "src" / "survaize" / "web" / "frontend"
        dist = frontend / "dist"

        print(f"Building frontend in {frontend}...")
        subprocess.run(["npm", "ci"], cwd=frontend, check=True)
        subprocess.run(["npm", "run", "build"], cwd=frontend, check=True)

        assert (dist / "index.html").exists(), "`npm run build` failed!"
