"""Thin command-line adapter around configuration, matching, and output."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from .config import load_filters
from .matching import evaluate


def write_env(path: Path, results: dict[str, bool]) -> None:
    """Replace output only after writing a complete file in the same directory."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(
                "".join(f"{name}={str(value).lower()}\n" for name, value in results.items())
            )
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate changed paths and write CI filter results."
    )
    parser.add_argument("--config", required=True, type=Path, help="YAML filter configuration")
    parser.add_argument(
        "--output", default=Path("filters.env"), type=Path, help="Output (filters.env)"
    )
    parser.add_argument("paths", nargs="+", help="Changed repository-relative POSIX paths")
    args = parser.parse_args(argv)

    try:
        if args.config.resolve() == args.output.resolve():
            raise ValueError("Configuration and output must be different files")
        filters = load_filters(args.config)
        results = evaluate(filters, args.paths)
        write_env(args.output, results)
    except ValueError as exc:
        parser.error(str(exc))
    except OSError as exc:
        print(f"cicd-filter: {exc}", file=sys.stderr)
        return 1
    return 0
