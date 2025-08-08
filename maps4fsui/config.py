import json
import os
from typing import Any, Literal

import maps4fs.generator.config as mfscfg
import requests

WORKING_DIRECTORY = os.getcwd()
DATA_DIRECTORY = os.path.join(WORKING_DIRECTORY, "data")
DOCS_DIRECTORY = os.path.join(WORKING_DIRECTORY, "docs")
os.makedirs(DOCS_DIRECTORY, exist_ok=True)
os.makedirs(DATA_DIRECTORY, exist_ok=True)
MD_FILES = {
    "📁 Map structure": "map_structure.md",
    "⛰️ DEM": "dem.md",
    "🎨 Textures": "textures.md",
    "🌾 Farmlands": "farmlands.md",
    "🚜 Fields": "fields.md",
}
FAQ_MD = os.path.join(DOCS_DIRECTORY, "FAQ.md")
VIDEO_TUTORIALS_PATH = os.path.join(WORKING_DIRECTORY, "maps4fsui", "videos.json")

INPUT_DIRECTORY = os.path.join(mfscfg.MFS_CACHE_DIR, "input")
os.makedirs(INPUT_DIRECTORY, exist_ok=True)


with open(VIDEO_TUTORIALS_PATH, "r", encoding="utf-8") as f:
    video_tutorials_json = json.load(f)

PUBLIC_HOSTNAME_KEY = "PUBLIC_HOSTNAME"
PUBLIC_HOSTNAME_VALUE = "maps4fs"


QUEUE_LIMIT = 3
DEFAULT_LAT = 45.28571409289627
DEFAULT_LON = 20.237433441210115

QUEUE_FILE = os.path.join(WORKING_DIRECTORY, "queue.json")
QUEUE_TIMEOUT = 120
QUEUE_INTERVAL = 10

REMOVE_DELAY = 300  # 5 minutes


def get_schema(game_code: str, schema_type: Literal["texture", "tree"]) -> list[dict[str, Any]]:
    """Get the schema for the specified game and schema type.

    Args:
        game_code (str): The game code.
        schema_type (Literal["texture", "tree"]): The schema type.

    Returns:
        list[dict[str, Any]]: The schema for the specified game and schema type.
    """
    game_code = game_code.lower()
    schema_path = os.path.join(DATA_DIRECTORY, f"{game_code}-{schema_type}-schema.json")

    if not os.path.isfile(schema_path):
        raise FileNotFoundError(f"{schema_type} for {game_code} not found in {schema_path}.")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    return schema


def get_mds() -> dict[str, str]:
    """Get the paths to the Markdown files in the docs directory.

    Returns:
        dict[str, str]: The paths to the Markdown files in the docs directory.
    """
    return {
        md_file: os.path.join(DOCS_DIRECTORY, filename) for md_file, filename in MD_FILES.items()
    }


def is_public() -> bool:
    """Check if the script is running on a public server.

    Returns:
        bool: True if the script is running on a public server, False otherwise.
    """
    return os.environ.get(PUBLIC_HOSTNAME_KEY) == PUBLIC_HOSTNAME_VALUE


def get_versions() -> tuple[str, str] | None:
    """Get the latest version and the current version of the package.

    Returns:
        tuple[str, str] | None: The latest version and the current version if the package is not
            the latest version, None otherwise
    """
    try:
        response = requests.get("https://pypi.org/pypi/maps4fs/json")
        response.raise_for_status()

        latest_version = response.json()["info"]["version"]

        current_version = mfscfg.get_package_version("maps4fs")
        if current_version == "unknown":
            # Skip version check if the current version is unknown (e.g., local development).
            current_version = latest_version

        return latest_version, current_version
    except Exception:
        return None
