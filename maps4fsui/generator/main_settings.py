from time import sleep

import config
import maps4fs as mfs
import osmp
import streamlit as st
from generator.base_component import BaseComponent
from generator.settings_templates import MainSettingsTemplate
from streamlit_folium import folium_static
from templates import Messages

GAME_OPTIONS = ["FS25", "FS22"]
DEFAULT_MAP_SIZES = [2048, 4096, 8192, 16384]


class MainSettings(BaseComponent):
    def __init__(self, public: bool, **kwargs):
        super().__init__(public, **kwargs)
        self.html_preview_container = kwargs["html_preview_container"]
        settings_template = kwargs.get("settings_template", {})
        try:
            self.template = MainSettingsTemplate(**settings_template)
        except TypeError:
            self.template = MainSettingsTemplate()

        st.write("Select the game for which you want to generate the map:")

        try:
            game_idx = GAME_OPTIONS.index(self.template.game)
        except ValueError:
            game_idx = 0

        self.game_code = st.selectbox(
            "Game",
            options=GAME_OPTIONS,
            key="game_code",
            label_visibility="collapsed",
            index=game_idx,
        )

        if self.game_code == "FS22":
            st.warning(Messages.FS22_NOTES, icon="💡")

        st.write("Enter latitude and longitude of the center point of the map:")
        self.lat_lon_input = st.text_input(
            "Latitude and Longitude",
            f"{self.template.latitude}, {self.template.longitude}",
            key="lat_lon",
            label_visibility="collapsed",
            on_change=self.map_preview,
        )

        size_options = DEFAULT_MAP_SIZES + ["Custom"]
        if self.public:
            size_options = size_options[:2]

        size = self.template.size
        try:
            if size not in DEFAULT_MAP_SIZES:
                size = "Custom"
            size_idx = size_options.index(size)
        except ValueError:
            size_idx = 0

        st.write("Select size of the map:")
        self.map_size_input = st.selectbox(
            "Map Size (meters)",
            options=size_options,
            label_visibility="collapsed",
            on_change=self.map_preview,
            index=size_idx,
        )

        self.output_size = None

        if self.public:
            st.warning(Messages.PUBLIC_MAP_SIZE, icon="💡")

        if self.map_size_input == "Custom":
            st.write("Enter map size (real world meters):")

            default_custom_value = 2048
            if size == "Custom":
                default_custom_value = self.template.size

            custom_map_size_input = st.number_input(
                label="Size (meters)",
                min_value=2,
                value=default_custom_value,
                key="custom_size",
                label_visibility="collapsed",
                on_change=self.map_preview,
            )
            self.map_size_input = custom_map_size_input

            st.write("Enter output map size (in-game meters):")
            self.output_size = st.number_input(
                label="Output Size (in-game meters)",
                min_value=2,
                value=2048,
                key="output_size",
                label_visibility="collapsed",
            )
            st.info(Messages.OUTPUT_SIZE_INFO)

        try:
            lat, lon = self.lat_lon
        except ValueError:
            lat, lon = config.DEFAULT_LAT, config.DEFAULT_LON

        dtm_provider = mfs.DTMProvider.get_provider_by_name(self.template.dtm_provider)
        if dtm_provider:
            self.template_provider_code = dtm_provider.code
        else:
            self.template_provider_code = None

        providers: dict[str, str] = mfs.DTMProvider.get_valid_provider_descriptions((lat, lon))
        provider_codes = list(providers.keys())

        try:
            provider_idx = provider_codes.index(self.template_provider_code())
        except ValueError:
            print("Provider not found")
            provider_idx = 0

        st.write("Select the DTM provider:")
        self.dtm_provider_code = st.selectbox(
            "DTM Provider",
            options=list(providers.keys()),
            format_func=lambda code: providers[code],
            key="dtm_provider",
            label_visibility="collapsed",
            # disabled=self.public,
            on_change=self.provider_info,
            index=provider_idx,
        )
        self.provider_settings = None
        self.provider_info_container: st.delta_generator.DeltaGenerator = st.empty()
        self.provider_info()

        st.write("Enter the rotation of the map:")

        self.rotation = st.slider(
            "Rotation",
            min_value=-180,
            max_value=180,
            value=self.template.rotation,
            step=1,
            key="rotation",
            label_visibility="collapsed",
            disabled=False,
            on_change=self.map_preview,
        )

    @property
    def lat_lon(self) -> tuple[float, float]:
        """Get the latitude and longitude of the center point of the map.

        Returns:
            tuple[float, float]: The latitude and longitude of the center point of the map.
        """
        return tuple(map(float, self.lat_lon_input.split(",")))

    def map_preview(self) -> None:
        """Generate a preview of the map in the HTML container.
        This method is called when the latitude, longitude, or map size is changed.
        """
        try:
            lat, lon = self.lat_lon
        except ValueError:
            return

        map_size = self.map_size_input
        map = osmp.get_rotated_preview(lat, lon, map_size, angle=-self.rotation)

        with self.html_preview_container:
            folium_static(map, height=600, width=600)

    def provider_info(self) -> None:
        provider_code = self.dtm_provider_code
        provider = mfs.DTMProvider.get_provider_by_code(provider_code)

        if provider is None:
            return

        self.provider_settings = None
        self.provider_info_container.empty()
        sleep(0.1)

        with self.provider_info_container:
            with st.container():
                if provider.instructions() is not None:
                    st.write(provider.instructions())

                if provider.settings() is not None:
                    provider_settings = provider.settings()()
                    settings = {}
                    settings_json = provider_settings.model_dump()
                    for raw_field_name, value in settings_json.items():
                        field_name = self.snake_to_human(raw_field_name)
                        widget = self._create_widget(
                            provider_code, field_name, raw_field_name, value
                        )

                        settings[raw_field_name] = widget

                    self.provider_settings = settings
