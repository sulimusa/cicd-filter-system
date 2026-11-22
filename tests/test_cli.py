import subprocess
import sys
from pathlib import Path

import pytest

from cicd_filter.cli import main, write_env

ROOT = Path(__file__).resolve().parents[1]


def test_assignment_example_through_installed_module(tmp_path):
    output = tmp_path / "results.env"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "cicd_filter",
            "--config",
            str(ROOT / "examples/filters.yaml"),
            "--output",
            str(output),
            "App.kt",
            "src/test/FiltersTest.kt",
            "README.md",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert output.read_bytes() == (ROOT / "examples/expected.env.txt").read_bytes()


def test_default_output_and_false_is_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--config", str(ROOT / "examples/filters.yaml"), "unrelated.txt"]) == 0
    assert (tmp_path / "filters.env").read_text() == (
        "kotlin_sources=false\ntests=false\ndocumentation=false\n"
    )


def test_invalid_configuration_does_not_overwrite_existing_output(tmp_path, capsys):
    config, output = tmp_path / "bad.yaml", tmp_path / "results.env"
    config.write_text("filters: []")
    output.write_text("previous=true\n")
    with pytest.raises(SystemExit) as exc:
        main(["--config", str(config), "--output", str(output), "App.kt"])
    assert exc.value.code == 2
    assert "non-empty mapping" in capsys.readouterr().err
    assert output.read_text() == "previous=true\n"


def test_invalid_path_leaves_no_output(tmp_path):
    output = tmp_path / "results.env"
    with pytest.raises(SystemExit) as exc:
        main(["--config", str(ROOT / "examples/filters.yaml"), "--output", str(output), "../x"])
    assert exc.value.code == 2
    assert not output.exists()


def test_input_output_collision_rejected(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("filters: {docs: ['README.md']}")
    before = config.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(["--config", str(config), "--output", str(config), "README.md"])
    assert exc.value.code == 2
    assert config.read_bytes() == before


def test_missing_input_is_clear_io_error(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "missing.yaml"), "README.md"]) == 1
    assert "cicd-filter:" in capsys.readouterr().err
    assert "Traceback" not in capsys.readouterr().err


def test_missing_output_directory(tmp_path, capsys):
    assert (
        main(
            [
                "--config",
                str(ROOT / "examples/filters.yaml"),
                "--output",
                str(tmp_path / "absent/results.env"),
                "README.md",
            ]
        )
        == 1
    )
    assert "cicd-filter:" in capsys.readouterr().err


def test_requires_changed_paths():
    with pytest.raises(SystemExit) as exc:
        main(["--config", "filters.yaml"])
    assert exc.value.code == 2


def test_atomic_write_replaces_previous_results(tmp_path):
    output = tmp_path / "results.env"
    output.write_text("old=true\n")
    write_env(output, {"backend": False, "docs": True})
    assert output.read_bytes() == b"backend=false\ndocs=true\n"
    assert list(tmp_path.iterdir()) == [output]


def test_failed_replace_preserves_output_and_removes_temporary(tmp_path, monkeypatch):
    output = tmp_path / "results.env"
    output.write_text("previous=true\n")

    def fail_replace(*args):
        raise PermissionError("simulated write failure")

    monkeypatch.setattr("cicd_filter.cli.os.replace", fail_replace)
    with pytest.raises(PermissionError):
        write_env(output, {"docs": True})
    assert output.read_text() == "previous=true\n"
    assert list(tmp_path.iterdir()) == [output]
