import yaml
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG = {
    "csv_path": "data.csv",
    "entity_col": None,
    "time_col": None,
    "value_col": None,
    "output_dir": ".",
    "frames_dir": "frames",
    "videos_dir": "videos",
    "thumbnails_dir": "thumbnails",
    "format": "landscape",
    "fps": 30,
    "duration_per_frame": 0.2,
    "intro_image": None,
    "intro_duration": 2.0,
    "outro_image": None,
    "outro_duration": 2.0,
    "audio_track": None,  # None = silent audio, or path to audio file
    "chart": {
        "style": None,
        "title_template": "Top 10 - {year}",
        "top_n": 10,
        "colors": None,
    },
}

VIDEO_FORMATS = {
    "shorts": {"width": 1080, "height": 1920, "aspect": "9:16"},
    "landscape": {"width": 1920, "height": 1080, "aspect": "16:9"},
    "square": {"width": 1080, "height": 1080, "aspect": "1:1"},
}


def load_config(config_path: str) -> Dict[str, Any]:
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f) or {}

    config = DEFAULT_CONFIG.copy()
    _deep_update(config, user_config)

    config["_config_dir"] = config_path.parent
    _resolve_paths(config)

    return config


def _deep_update(base: dict, update: dict) -> None:
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def resolve_path(
    config: Dict[str, Any], relative_path: Optional[str]
) -> Optional[Path]:
    if relative_path is None:
        return None
    config_dir = config["_config_dir"]
    path = config_dir / relative_path
    return path.resolve()


def _resolve_paths(config: Dict[str, Any]) -> None:
    config["csv_path"] = resolve_path(config, config.get("csv_path"))
    config["intro_image"] = resolve_path(config, config.get("intro_image"))
    config["outro_image"] = resolve_path(config, config.get("outro_image"))
    config["audio_track"] = resolve_path(config, config.get("audio_track"))

    output_dir = config["_config_dir"] / config.get("output_dir", ".")
    config["_output_dir"] = output_dir.resolve()
    config["_frames_dir"] = output_dir / config.get("frames_dir", "frames")
    config["_videos_dir"] = output_dir / config.get("videos_dir", "videos")
    config["_thumbnails_dir"] = output_dir / config.get("thumbnails_dir", "thumbnails")


def get_video_resolution(format_name: str) -> tuple[int, int]:
    if format_name not in VIDEO_FORMATS:
        raise ValueError(
            f"Unknown format: {format_name}. Choose from: {list(VIDEO_FORMATS.keys())}"
        )
    fmt = VIDEO_FORMATS[format_name]
    return fmt["width"], fmt["height"]
