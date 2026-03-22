from __future__ import annotations

import os
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

ConfigDict = dict[str, dict[str, Any]]


def _xdg_config_home() -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".config"


CONFIG_DIR = _xdg_config_home() / "crossref-tool"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG: ConfigDict = {
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


def _merge(base: ConfigDict, override: dict[str, Any]) -> ConfigDict:
    merged = deepcopy(base)
    for key, value in override.items():
        if not isinstance(value, dict):
            continue
        existing = merged.get(key, {})
        section = deepcopy(existing)
        section.update(value)
        merged[key] = section
    return merged


def load_config() -> ConfigDict:
    if not CONFIG_PATH.exists():
        return deepcopy(DEFAULT_CONFIG)
    with CONFIG_PATH.open("rb") as handle:
        loaded = tomllib.load(handle)
    return _merge(DEFAULT_CONFIG, loaded)


def save_config(config: ConfigDict) -> None:
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


def reset_config() -> ConfigDict:
    config = deepcopy(DEFAULT_CONFIG)
    save_config(config)
    return config
