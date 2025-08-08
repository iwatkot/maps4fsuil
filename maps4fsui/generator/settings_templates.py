from typing import Literal, NamedTuple

import config


class MainSettingsTemplate(NamedTuple):
    game: Literal["FS25", "FS22"] = "FS25"
    latitude: float = config.DEFAULT_LAT
    longitude: float = config.DEFAULT_LON
    size: int = 2048
    rotation: int = 0
    dtm_provider: str = "SRTM 30 m"
