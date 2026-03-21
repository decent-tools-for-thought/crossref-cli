from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import tomllib

def _xdg_config_home() -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".config"


CONFIG_DIR = _xdg_config_home() / "crossref-tool"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = {
    "api": {
        "base_url": "https://api.crossref.org",
    },
    "pool": {
        "default": "public",
        "email": "",
        "api_key": "",
    },
    "works": {
        "default_rows": 20,
        "max_rows": 1000,
    },
    "output": {
        "default_format": "jsonl",
        "default_select": "DOI,title,author,published-online,URL,type",
    },
}


def _merge(base: dict, override: dict) -> dict:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return deepcopy(DEFAULT_CONFIG)
    with CONFIG_PATH.open("rb") as handle:
        loaded = tomllib.load(handle)
    return _merge(DEFAULT_CONFIG, loaded)


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for section, values in config.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            if isinstance(value, bool):
                encoded = "true" if value else "false"
            elif isinstance(value, int):
                encoded = str(value)
            else:
                escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
                encoded = f'"{escaped}"'
            lines.append(f"{key} = {encoded}")
        lines.append("")
    CONFIG_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def reset_config() -> dict:
    config = deepcopy(DEFAULT_CONFIG)
    save_config(config)
    return config
