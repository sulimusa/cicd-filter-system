"""Match the assignment's small glob language, without filesystem access."""

import re
from dataclasses import dataclass
from functools import cache


def split_path(value: str) -> tuple[str, ...]:
    """Require an unambiguous repository-relative POSIX path."""
    parts = tuple(value.split("/"))
    if (
        not value
        or "\\" in value
        or any(part in ("", ".", "..") for part in parts)
        or any(char in value for char in "\r\n\x00")
    ):
        raise ValueError(f"Expected a repository-relative POSIX path, got {value!r}")
    return parts


@dataclass(frozen=True)
class Glob:
    # None represents **; other segments contain a compiled *-aware expression.
    segments: tuple[re.Pattern[str] | None, ...]

    @classmethod
    def compile(cls, pattern: str) -> "Glob":
        segments = []
        for part in split_path(pattern):
            if part == "**":
                segments.append(None)
            else:
                if "**" in part:
                    raise ValueError("** must occupy a whole path segment")
                expression = ".*".join(re.escape(piece) for piece in part.split("*"))
                segments.append(re.compile(expression))
        return cls(tuple(segments))

    def matches(self, path: tuple[str, ...]) -> bool:
        @cache
        def match(pattern_index: int, path_index: int) -> bool:
            if pattern_index == len(self.segments):
                return path_index == len(path)
            segment = self.segments[pattern_index]
            if segment is None:
                # ** consumes zero segments, or one segment and keeps matching.
                return match(pattern_index + 1, path_index) or (
                    path_index < len(path) and match(pattern_index, path_index + 1)
                )
            return (
                path_index < len(path)
                and segment.fullmatch(path[path_index]) is not None
                and match(pattern_index + 1, path_index + 1)
            )

        return match(0, 0)


@dataclass(frozen=True)
class Filter:
    includes: tuple[Glob, ...]
    excludes: tuple[Glob, ...]

    def matches(self, paths: tuple[tuple[str, ...], ...]) -> bool:
        return any(
            any(glob.matches(path) for glob in self.includes)
            and not any(glob.matches(path) for glob in self.excludes)
            for path in paths
        )


def evaluate(filters: dict[str, Filter], changed_paths: list[str]) -> dict[str, bool]:
    paths = tuple(split_path(path) for path in changed_paths)
    return {name: rule.matches(paths) for name, rule in filters.items()}
