"""
Configuration loader. Reads YAML configs from Drive.
All config access goes through this module.
Never read config files directly in other modules.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional
from functools import lru_cache


class ConfigLoader:
    """
    Loads and caches configuration from YAML files.
    Resolves environment variable references in values.

    Args:
        config_dir: Path to config directory on Drive
    """

    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self._cache = {}

    def load(self, filename: str) -> dict:
        """
        Loads a config file by name.
        Caches result. Call reload() to force refresh.

        Args:
            filename: Config filename (e.g. 'llm_config.yaml')

        Returns:
            Parsed config dict with env vars resolved

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config is malformed
        """
        if filename in self._cache:
            return self._cache[filename]

        config_path = self.config_dir / filename
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}"
                f"Run the scaffold cell to create default configs."
            )

        with open(config_path) as f:
            raw = yaml.safe_load(f)

        resolved = self._resolve_env_vars(raw)
        self._cache[filename] = resolved
        return resolved

    def reload(self, filename: str) -> dict:
        """Force reload a config file, clearing cache."""
        self._cache.pop(filename, None)
        return self.load(filename)

    def _resolve_env_vars(self, obj: Any) -> Any:
        """Recursively resolve ${ENV_VAR} references in config values."""
        if isinstance(obj, str):
            if obj.startswith("${") and obj.endswith("}"):
                env_key = obj[2:-1]
                value = os.environ.get(env_key)
                if value is None:
                    return obj  # leave as-is, not an error yet
                return value
            return obj
        elif isinstance(obj, dict):
            return {k: self._resolve_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_env_vars(i) for i in obj]
        return obj
