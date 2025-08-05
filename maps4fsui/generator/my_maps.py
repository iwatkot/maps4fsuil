import json
import os
import re
import shutil
from typing import Generator, Literal, NamedTuple

import maps4fs.generator.config as mfscfg
import streamlit as st
from maps4fs.generator.settings import GenerationSettings, MainSettings
from PIL import Image

DIR_PATTERN = r"^(\d+_\d+)_fs"


class MapEntry(NamedTuple):
    """Represents a map entry with its directory, main settings, and generation settings."""

    directory: str
    main_settings: MainSettings
    generation_settings: GenerationSettings

    def get_ui(self):
        with st.container(border=True):
            info_column, previews_column = st.columns([3, 1], gap="large")
            with info_column:
                st.subheader(f"{self.main_settings.date} at {self.main_settings.time}")

                st.markdown(self._badges())

                st.markdown(
                    f"**Coordinates:** `{self.main_settings.latitude}, {self.main_settings.longitude}`  \n"
                    f"**Country:** {self.main_settings.country}  \n"
                    f"**Size:** {self.main_settings.size}  \n"
                    f"**Rotation:** {self.main_settings.rotation}  \n"
                    f"**DTM Provider:** {self.main_settings.dtm_provider}  \n"
                    "**Generation Settings:**"
                )
                st.json(self.generation_settings.to_json(), expanded=False)

                left, middle, right, *_ = st.columns([1, 1, 1, 3])
                with left:
                    archive_path = self._archive()
                    with open(archive_path, "rb") as f:
                        st.download_button(
                            label="Download",
                            data=f,
                            file_name=f"{archive_path.split('/')[-1]}",
                            mime="application/zip",
                            icon="📥",
                            use_container_width=True,
                            key=f"download_{self.directory}",
                        )
                with middle:
                    st.button(
                        "Repeat",
                        use_container_width=True,
                        icon="🔁",
                        disabled=True,
                        help="Will be available soon",
                        key=f"repeat_{self.directory}",
                    )
                with right:
                    if st.button(
                        label="Delete",
                        use_container_width=True,
                        icon="🗑️",
                        key=f"delete_{self.directory}",
                    ):
                        try:
                            shutil.rmtree(self.directory)
                            archive_path = self._archive(do_not_check=True)
                            if os.path.isfile(archive_path):
                                os.remove(archive_path)

                            st.success("Map deleted successfully.")
                        except Exception:
                            pass
                        st.warning("Map deletion failed.")
            with previews_column:
                image_preview_paths = self._previews()
                for row in range(0, len(image_preview_paths), 2):
                    columns = st.columns(2)
                    for column, image_preview_path in zip(
                        columns, image_preview_paths[row : row + 2]
                    ):
                        if not os.path.isfile(image_preview_path):
                            continue
                        try:
                            image = Image.open(image_preview_path)
                            column.image(image, use_container_width=True)
                        except Exception:
                            continue

    @property
    def completed(self) -> bool:
        """Check if the map entry is complete based on its main settings.

        Returns:
            bool: True if the map entry is complete, False otherwise.
        """
        return self.main_settings.completed

    @property
    def error(self) -> bool:
        """Check if the map entry has an error based on its main settings.

        Returns:
            bool: True if the map entry has an error, False otherwise.
        """
        return self.main_settings.error

    @property
    def api_request(self) -> bool:
        """Check if the map entry was generated using an API request.

        Returns:
            bool: True if the map entry was generated using an API request, False otherwise.
        """
        return self.main_settings.api_request

    def matches_filter(
        self, filters: list[Literal["Complete", "Incomplete", "Error", "API"]]
    ) -> bool:
        """Filter the map entry based on the provided filters.

        Args:
            filters (list): List of filters to apply.

        Returns:
            bool: True if the map entry matches any of the filters, False otherwise.
        """
        if not filters:
            return True

        filter_map = {
            "Complete": self.completed,
            "Incomplete": not self.completed,
            "Error": self.error,
            "API": self.api_request,
        }
        for filter_name in filters:
            if filter_name in filter_map and filter_map[filter_name]:
                return True
        return False

    def _badges(self) -> str:
        """Generate badges based on the main settings of the map entry.

        Returns:
            str: A string containing badges representing the map's main settings.
        """
        badges = []
        badges.append(
            f":blue-badge[{self.main_settings.game.upper()}] "
            f":blue-badge[{self.main_settings.version}]"
        )
        if self.main_settings.custom_osm:
            badges.append(":violet-badge[Custom OSM]")
        if self.main_settings.api_request:
            badges.append(":orange-badge[API]")
        if not self.main_settings.completed:
            badges.append(":red-badge[Incomplete]")
        else:
            badges.append(":green-badge[Complete]")
        if self.main_settings.error:
            badges.append(":red-badge[Error]")
        return " ".join(badges)

    def _previews(self) -> list[str]:
        """Get a list of preview image paths for the map entry.

        Returns:
            list[str]: A list of file paths to preview images.
        """
        previews = []
        previews_directory = os.path.join(self.directory, "previews")
        if not os.path.isdir(previews_directory):
            return previews

        useful_previews = [
            "textures_osm.png",
            "dem_colored.png",
            "farmlands.png",
            "background_dem.png",
        ]

        for file_name in useful_previews:
            file_path = os.path.join(previews_directory, file_name)
            if os.path.isfile(file_path):
                previews.append(file_path)
        return previews

    def _archive(self, do_not_check: bool = False) -> str:
        directory_name = os.path.basename(self.directory)
        full_archive_path = os.path.join(mfscfg.MFS_DATA_DIR, f"{directory_name}.zip")
        archive_path = full_archive_path.replace(".zip", "")

        if not os.path.isfile(full_archive_path):
            shutil.make_archive(archive_path, "zip", self.directory)

        return full_archive_path


class MyMapsUI:
    """UI for displaying list of previously generated maps."""

    def __init__(self):
        filters = [
            "Complete",
            "Incomplete",
            "Error",
            "API",
        ]
        self.filter = st.pills(
            "Filter maps",
            options=filters,
            selection_mode="multi",
            default=["Complete"],
            disabled=True,
            help="Will be available soon",
        )

        self.search_input = st.text_input(
            "Search",
            placeholder="Search by coordinates",
            label_visibility="collapsed",
            disabled=True,
            help="Will be available soon",
        )

        st.warning(
            "Warning: beta feature, expect errors and bugs.",
            icon="⚠️",
        )

        for directory_name in self.find_map_directories():
            directory_path = os.path.join(mfscfg.MFS_DATA_DIR, directory_name)

            map_entry = self.get_map_entry(directory_path)
            if map_entry:
                map_entry.get_ui()

    @staticmethod
    def find_map_directories(directory: str = mfscfg.MFS_DATA_DIR) -> Generator[str, None, None]:
        """Find directories that match the map directory pattern and yield their names.

        Args:
            directory (str): The directory to search in. Defaults to mfscfg.MFS_DATA_DIR.

        Yields:
            str: The names of directories that match the map directory pattern.
        """
        matches = []
        for entry in os.listdir(directory):
            if os.path.isdir(os.path.join(directory, entry)):
                match = re.match(DIR_PATTERN, entry)
                if match:
                    matches.append(entry)
        matches = sorted(matches, reverse=True)

        yield from matches

    @staticmethod
    def get_map_entry(directory_path: str) -> MapEntry | None:
        """Get the map entry for a given directory path.

        Args:
            directory_path (str): The path of the directory.

        Returns:
            MapEntry: A named tuple containing main settings and generation settings.
        """
        main_settings_path = os.path.join(directory_path, "main_settings.json")
        generation_settings = os.path.join(directory_path, "generation_settings.json")
        if not os.path.isfile(main_settings_path) or not os.path.isfile(generation_settings):
            return None

        try:
            with open(main_settings_path, "r") as f:
                main_settings_data = json.load(f)

            with open(generation_settings, "r") as f:
                generation_settings_data = json.load(f)
        except json.JSONDecodeError:
            return None

        try:
            main_settings = MainSettings.from_json(main_settings_data)
            generation_settings = GenerationSettings.from_json(generation_settings_data)
        except Exception:
            return None

        return MapEntry(directory_path, main_settings, generation_settings)
