"""Safe YAML loading and explicit validation of the filter schema."""

import re
from pathlib import Path

import yaml
from yaml.constructor import ConstructorError

from .matching import Filter, Glob


class ConfigError(ValueError):
    """An invalid configuration, suitable for a concise CLI error."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Do not silently overwrite duplicate filter names or YAML keys."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ConstructorError(None, None, "YAML keys must be strings", key_node.start_mark)
            if key in seen:
                raise ConstructorError(None, None, f"Duplicate key: {key}", key_node.start_mark)
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_filters(path: Path) -> dict[str, Filter]:
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (yaml.YAMLError, UnicodeError) as exc:
        raise ConfigError(f"Invalid YAML: {exc}") from exc

    if not isinstance(data, dict) or set(data) != {"filters"}:
        raise ConfigError("Expected a YAML mapping with exactly one top-level key: filters")
    if not isinstance(data["filters"], dict) or not data["filters"]:
        raise ConfigError("filters must be a non-empty mapping")

    result = {}
    for name, patterns in data["filters"].items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ConfigError(f"Invalid environment variable name: {name!r}")
        if not isinstance(patterns, list):
            raise ConfigError(f"Filter {name!r} must contain a list of patterns")
        includes, excludes = [], []
        for pattern in patterns:
            if not isinstance(pattern, str) or not pattern:
                raise ConfigError(f"Filter {name!r}: each pattern must be a non-empty string")
            excluded = pattern.startswith("!")
            try:
                glob = Glob.compile(pattern[1:] if excluded else pattern)
            except ValueError as exc:
                raise ConfigError(f"Filter {name!r}, pattern {pattern!r}: {exc}") from exc
            (excludes if excluded else includes).append(glob)
        result[name] = Filter(tuple(includes), tuple(excludes))
    return result
