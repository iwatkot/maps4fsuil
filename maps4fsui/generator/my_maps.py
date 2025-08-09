import json
import math
import os
import re
import shutil
from typing import Literal

import config
import maps4fs.generator.config as mfscfg
import streamlit as st
from maps4fs.generator.settings import GenerationSettings, MainSettings
from PIL import Image

DIR_PATTERN = r"^(\d+_\d+)_fs"
PAGE_SIZE = 5


class Parameters:
    COMPLETE = "Complete"
    INCOMPLETE = "Incomplete"
    ERROR = "Error"
    API = "API"


class MapEntry:
    """Represents a map entry with its directory, main settings, and generation settings."""

    directory: str
    main_settings: MainSettings
    generation_settings: GenerationSettings

    def __init__(
        self,
        directory: str,
        main_settings: MainSettings,
        generation_settings: GenerationSettings,
        page: int,
    ):
        self.directory = directory
        self.directory_name = os.path.basename(directory)
        self.main_settings = main_settings
        self.generation_settings = generation_settings
        self.name = self._find_name(directory)
        self.page = page
        self.settings_applied = False

    def get_ui(self):
        with st.container(border=True):
            info_column, previews_column = st.columns([2, 1], gap="large")
            with info_column:
                self.name_input = st.text_input(
                    "name",
                    value=self.name,
                    label_visibility="collapsed",
                    key=f"name_{self.directory}_input_{self.page}",
                    on_change=self.rename_map_entry,
                )

                st.markdown(self._badges())

                st.markdown(self._asset_badges())

                st.markdown(
                    f"**Date and Time:** `{self.main_settings.date} at {self.main_settings.time}`  \n"
                    f"**Coordinates:** `{self.main_settings.latitude}, {self.main_settings.longitude}`  \n"
                    f"**Country:** {self.main_settings.country}  \n"
                    f"**Size:** {self.main_settings.size}  \n"
                    f"**Output Size:** {self.main_settings.output_size}  \n"
                    f"**Rotation:** {self.main_settings.rotation}  \n"
                    f"**DTM Provider:** {self.main_settings.dtm_provider}  \n"
                    "**Generation Settings:**"
                )
                st.json(self.generation_settings.to_json(), expanded=False)

                buttons_container = st.empty()
                with buttons_container:
                    with st.container():
                        left, middle, right, *_ = st.columns([1, 1, 1])
                        with left:
                            download_container = st.empty()
                            with download_container:
                                if st.button(
                                    "Prepare download",
                                    icon="📦",
                                    use_container_width=True,
                                    key=f"prepare_{self.directory}_{self.page}",
                                ):
                                    with download_container:
                                        archive_path = self._archive()
                                        with open(archive_path, "rb") as f:
                                            st.download_button(
                                                label="Download",
                                                data=f,
                                                file_name=f"{archive_path.split('/')[-1]}",
                                                mime="application/zip",
                                                icon="📥",
                                                use_container_width=True,
                                                key=f"download_{self.directory}_{self.page}",
                                            )
                        with middle:
                            if st.button(
                                "Repeat",
                                use_container_width=True,
                                icon="🔁",
                                key=f"repeat_{self.directory}_{self.page}",
                                disabled=config.is_public(),
                            ):
                                self.to_file()
                                self.settings_applied = True

                        with right:
                            if st.button(
                                label="Delete",
                                use_container_width=True,
                                icon="🗑️",
                                key=f"delete_{self.directory}_{self.page}",
                            ):
                                try:
                                    shutil.rmtree(self.directory)
                                    archive_path = self._archive(do_not_check=True)
                                    if os.path.isfile(archive_path):
                                        os.remove(archive_path)
                                    res = True
                                except Exception:
                                    res = False
                                with buttons_container:
                                    if res:
                                        st.success(
                                            "Map entry deleted successfully.",
                                            icon="✅",
                                        )
                                    else:
                                        st.error(
                                            "Failed to delete map entry.",
                                            icon="❌",
                                        )
            if self.settings_applied:
                st.success("Settings applied, please reload the page.", icon="✅")

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
            Parameters.COMPLETE: self.completed,
            Parameters.INCOMPLETE: not self.completed,
            Parameters.ERROR: self.error,
            Parameters.API: self.api_request,
        }
        for filter_name in filters:
            if filter_name in filter_map and filter_map[filter_name]:
                return True
        return False

    def matches_search(self, search_input: str, public: bool = False) -> bool:
        """Check if the map entry matches the search input.

        Args:
            search_input (str): The search input to match against.
            public (bool): Whether the app is running in public mode.

        Returns:
            bool: True if the map entry matches the search input, False otherwise.
        """
        if public:
            return search_input.lower() == self.directory_name.lower()

        if not search_input:
            return True

        return search_input.lower() in self.name.lower()

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

    def _asset_badges(self) -> str:
        badges = []

        # Most important assets.
        if self.generation_settings.background_settings.generate_background:
            badges.append(":green-badge[Background]")
        if self.generation_settings.background_settings.generate_water:
            badges.append(":blue-badge[Water]")
        if self.generation_settings.texture_settings.dissolve:
            badges.append(":grey-badge[Dissolved]")
        if self.generation_settings.satellite_settings.download_images:
            badges.append(":orange-badge[Satellite Images]")

        # Less important assets.
        if self.generation_settings.dem_settings.add_foundations:
            badges.append(":grey-badge[Foundations]")
        if self.generation_settings.background_settings.flatten_roads:
            badges.append(":grey-badge[Flatten Roads]")
        if self.generation_settings.grle_settings.add_grass:
            badges.append(":green-badge[Grass]")
        if self.generation_settings.grle_settings.random_plants:
            badges.append(":green-badge[Random Plants]")
        if self.generation_settings.i3d_settings.add_trees:
            badges.append(":green-badge[Trees]")

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

    def _find_name(self, directory: str) -> str:
        name_file_path = os.path.join(directory, "name.txt")
        if not os.path.isfile(name_file_path):
            name = self._default_name()
            self.update_name(name)

        with open(name_file_path, "r") as f:
            name = f.read().strip()
        if not name:
            name = self._default_name()
            self.update_name(name)
        return name

    def _default_name(self) -> str:
        """Generate a default name for the map entry based on its main settings.

        Returns:
            str: A default name for the map entry.
        """
        return (
            f"{self.main_settings.date} at {self.main_settings.time} - "
            f"{self.main_settings.latitude}, {self.main_settings.longitude}"
        )

    def update_name(self, new_name: str | None = None) -> None:
        """Update the name of the map entry and save it to a file.

        Args:
            new_name (str): The new name for the map entry.
        """
        self.name = new_name or self._default_name()
        name_file_path = os.path.join(self.directory, "name.txt")
        with open(name_file_path, "w") as f:
            f.write(new_name)

    def rename_map_entry(self) -> None:
        """Callback function to handle renaming of the map entry.

        Args:
            new_name (str): The new name for the map entry.
        """
        name_input = st.session_state.get(f"name_{self.directory}_input_{self.page}")
        if name_input and name_input != self.name:
            self.update_name(name_input)

    def to_json(self) -> dict[str, dict[str, str | int | float]]:
        main_settings = {
            "game": self.main_settings.game,
            "latitude": self.main_settings.latitude,
            "longitude": self.main_settings.longitude,
            "size": self.main_settings.size,
            "output_size": self.main_settings.output_size,
            "rotation": self.main_settings.rotation,
            "dtm_provider": self.main_settings.dtm_provider,
        }
        generation_settings = self.generation_settings.to_json()

        additional_settings = {
            "custom_osm": self.custom_osm,
        }

        return {
            "main_settings": main_settings,
            "generation_settings": generation_settings,
            "additional_settings": additional_settings,
        }

    def to_file(self, save_path: str | None = None) -> str:
        save_path = save_path or config.ONE_TIME_SETTINGS_PATH
        with open(save_path, "w") as f:
            json.dump(self.to_json(), f, indent=4)
        return save_path

    @property
    def custom_osm(self) -> str | None:
        custom_osm_path = os.path.join(self.directory, "custom_osm.osm")
        if self.main_settings.custom_osm and os.path.isfile(custom_osm_path):
            return custom_osm_path
        return None


class MyMapsUI:
    """UI for displaying list of previously generated maps."""

    def __init__(self, public: bool):
        self.public = public

        filters = [
            Parameters.COMPLETE,
            Parameters.INCOMPLETE,
            Parameters.ERROR,
            Parameters.API,
        ]

        if self.public:
            self.filter = filters
        else:
            self.filter = st.pills(
                "Filter maps",
                options=filters,
                selection_mode="multi",
                default=[Parameters.COMPLETE],
                label_visibility="collapsed",
            )

        self.search_input = st.text_input(
            "Search",
            placeholder="Search by name",
            label_visibility="collapsed",
            key="search_my_maps_input",
        )

        if self.public:
            if not self.search_input:
                st.error("On public version of the app you must provide your unique map name.")
                return

        total_directories = self.find_map_directories()
        self.total_pages = math.ceil(len(total_directories) / PAGE_SIZE)
        if "current_page" not in st.session_state:
            st.session_state.current_page = 1

        if "total_pages" not in st.session_state:
            st.session_state.total_pages = self.total_pages

        self.main_content = st.empty()

        self.page = st.session_state.current_page
        self.build_page()

        if self.total_pages > 1:
            with st.container():
                _, left, middle, right, _ = st.columns([1, 1, 1, 1, 1])
                with left:
                    st.button(
                        "Previous",
                        disabled=st.session_state.current_page == 1,
                        use_container_width=True,
                        type="tertiary",
                        on_click=self.previous_page,
                    )
                with middle:
                    st.button(
                        f"{st.session_state.current_page} / {st.session_state.total_pages}",
                        use_container_width=True,
                        type="tertiary",
                    )
                with right:
                    st.button(
                        "Next",
                        disabled=st.session_state.current_page == st.session_state.total_pages,
                        use_container_width=True,
                        type="tertiary",
                        on_click=self.next_page,
                    )

    def previous_page(self):
        if st.session_state.current_page > 1:
            st.session_state.current_page -= 1
            self.build_page()

    def next_page(self):
        if st.session_state.current_page < self.total_pages:
            st.session_state.current_page += 1
            self.build_page()

    def update_total_pages(self, filtered_elements_count: int):
        st.session_state.total_pages = math.ceil(filtered_elements_count / PAGE_SIZE)

    def build_page(self):
        map_directories = self.find_map_directories()

        all_map_entries = []
        for directory_name in map_directories:
            directory_path = os.path.join(mfscfg.MFS_DATA_DIR, directory_name)

            map_entry = self.get_map_entry(directory_path, self.page)
            if map_entry:
                all_map_entries.append(map_entry)

        filtered_map_entries = []
        for map_entry in all_map_entries:
            if map_entry.matches_filter(self.filter) and map_entry.matches_search(
                self.search_input, public=self.public
            ):
                filtered_map_entries.append(map_entry)

        self.update_total_pages(len(filtered_map_entries))

        if not filtered_map_entries:
            st.warning("No maps found matching the current filters.")

        first_idx = (st.session_state.current_page - 1) * PAGE_SIZE
        last_idx = first_idx + PAGE_SIZE
        last_idx = min(last_idx, len(filtered_map_entries))

        with self.main_content:
            with st.container():
                for map_entry in filtered_map_entries[first_idx:last_idx]:
                    map_entry.get_ui()

    @staticmethod
    def find_map_directories(
        directory: str = mfscfg.MFS_DATA_DIR, use_pattern: bool = True
    ) -> list[str]:
        """Find directories that match the map directory pattern and yield their names.

        Args:
            directory (str): The directory to search in. Defaults to mfscfg.MFS_DATA_DIR.
            use_pattern (bool): Whether to use the directory pattern for matching. Defaults to True.

        Returns:
            list[str]: A list of directory names that match the pattern.
        """
        matches = []
        for entry in os.listdir(directory):
            if os.path.isdir(os.path.join(directory, entry)):
                if not use_pattern:
                    matches.append(entry)
                else:
                    match = re.match(DIR_PATTERN, entry)
                    if match:
                        matches.append(entry)
        matches = sorted(matches, reverse=True)

        return matches

    @staticmethod
    def get_map_entry(directory_path: str, page: int) -> MapEntry | None:
        """Get the map entry for a given directory path.

        Args:
            directory_path (str): The path of the directory.
            page (int): The page number.

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

        return MapEntry(directory_path, main_settings, generation_settings, page)
