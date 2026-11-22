import pytest

from cicd_filter.matching import Filter, Glob, evaluate, split_path


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("README.md", "README.md", True),
        ("README.md", "docs/README.md", False),
        ("README.md", "readme.md", False),
        ("*.kt", "App.kt", True),
        ("*.kt", "src/App.kt", False),
        ("app/src/**/*.kt", "app/src/App.kt", True),
        ("app/src/**/*.kt", "app/src/main/kotlin/App.kt", True),
        ("app/src/**/*.kt", "other/app/src/App.kt", False),
        ("**/*.kt", "App.kt", True),
        ("**/*.kt", "src/main/App.kt", True),
        ("**/*.kt", "src/main/App.kt.bak", False),
        ("**/test/**", "test/Test.kt", True),
        ("**/test/**", "src/test/unit/Test.kt", True),
        ("**/test/**", "src/testing/Test.kt", False),
        ("**/test/**/*.kt", "src/test/Test.kt", True),
        ("**/test/**/*.kt", "src/test/unit/Test.kt", True),
        ("docs/**", "docs", True),  # ** can consume zero segments.
        ("docs/**", "docs/nested/page.md", True),
        ("**", "anything/nested/file", True),
        ("**/**/a", "a", True),
        ("**/**/a", "x/y/a", True),
        ("docs/*", "docs/nested/page.md", False),
        ("file*.txt", "file.txt", True),
        ("**/*", ".hidden", True),
        ("a[1].txt", "a[1].txt", True),  # Only * and ** are operators.
        ("a[1].txt", "a1.txt", False),
        ("file?.txt", "fileA.txt", False),
        ("a+b.txt", "aab.txt", False),
        ("**/*.kt", "folder with spaces/App.kt", True),
    ],
)
def test_glob_semantics(pattern, path, expected):
    assert Glob.compile(pattern).matches(split_path(path)) is expected


def rule(includes=(), excludes=()):
    return Filter(tuple(map(Glob.compile, includes)), tuple(map(Glob.compile, excludes)))


def test_excluded_file_does_not_veto_another_included_file():
    filters = {"backend": rule(["**/*.kt"], ["**/test/**"])}
    assert evaluate(filters, ["src/test/Test.kt", "src/App.kt"]) == {"backend": True}
    assert evaluate(filters, ["src/App.kt", "src/test/Test.kt"]) == {"backend": True}
    assert evaluate(filters, ["src/test/Test.kt"]) == {"backend": False}


def test_any_inclusion_and_any_exclusion():
    filters = {"frontend": rule(["web/**/*.ts", "web/**/*.tsx"], ["**/test/**", "**/vendor/**"])}
    assert evaluate(filters, ["web/App.tsx"]) == {"frontend": True}
    assert evaluate(filters, ["web/test/a.ts", "web/vendor/b.tsx"]) == {"frontend": False}


def test_no_inclusion_means_false():
    filters = {"empty": rule(), "only_exclusions": rule(excludes=["docs/**"])}
    assert evaluate(filters, ["App.kt"]) == {"empty": False, "only_exclusions": False}


def test_no_matching_paths_and_duplicate_paths():
    filters = {"backend": rule(["**/*.kt"])}
    assert evaluate(filters, []) == {"backend": False}
    assert evaluate(filters, ["README.md"]) == {"backend": False}
    assert evaluate(filters, ["App.kt", "App.kt"]) == {"backend": True}


@pytest.mark.parametrize("path", ["", "/src/a", "./a", "a/../b", "a//b", "a/", "a\\b", "a\nb"])
def test_invalid_paths(path):
    with pytest.raises(ValueError, match="repository-relative"):
        split_path(path)


def test_globstar_requires_whole_segment():
    with pytest.raises(ValueError, match="whole path segment"):
        Glob.compile("src/a**b.kt")
