from pathlib import Path


def get_project_root_path() -> Path:
    """Returns the path to the project root directory (i.e. the directory containing the pyproject.toml file)."""
    return Path(__file__).parent.parent.parent.parent.resolve()
