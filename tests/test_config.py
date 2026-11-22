import pytest

from cicd_filter.config import ConfigError, load_filters
from cicd_filter.matching import evaluate


@pytest.mark.parametrize(
    "text",
    [
        "",
        "[]",
        "filters: []",
        "filters: {}",
        "filters: null",
        "filter: {}",
        "filters: {docs: []}\nextra: true",
        "filters: {bad-name: []}",
        "filters: {123: []}",
        "filters: {true: []}",
        "filters: {docs: '*.md'}",
        "filters: {docs: [123]}",
        "filters: {docs: ['']}",
        "filters: {docs: ['!']}",
        "filters: {docs: ['src/a**b']}",
        "filters: {docs: ['/absolute']}",
        "filters: {docs: ['../outside']}",
        "filters: {docs: ['a'], docs: ['b']}",
        "filters: {docs: ['a']}\nfilters: {docs: ['b']}",
        "filters: [",
        "filters: !!python/object:builtins.object {}",
    ],
)
def test_rejects_invalid_configuration(tmp_path, text):
    path = tmp_path / "filters.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError):
        load_filters(path)


def test_non_utf8_configuration(tmp_path):
    path = tmp_path / "filters.yaml"
    path.write_bytes(b"\xff")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_filters(path)


def test_order_independent_exclusions_and_empty_patterns(tmp_path):
    path = tmp_path / "filters.yaml"
    path.write_text("filters:\n  backend: ['!**/test/**', '**/*.kt']\n  empty: []\n")
    filters = load_filters(path)
    assert list(filters) == ["backend", "empty"]
    assert evaluate(filters, ["src/App.kt", "src/test/Test.kt"]) == {
        "backend": True,
        "empty": False,
    }


def test_missing_file_is_an_io_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_filters(tmp_path / "missing.yaml")
