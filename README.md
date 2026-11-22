# CI/CD Filter System

A Python CLI that checks changed file paths against named YAML filters and writes
one `true` or `false` result per filter to a dotenv file. A downstream CI job can
use those values to decide which work to run.

## Setup

Requires Python 3.11 or newer. From the repository root, run:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Run the example

```sh
cicd-filter --config examples/filters.yaml --output filters.env \
  App.kt src/test/FiltersTest.kt README.md

cat filters.env
```

Expected output:

```text
kotlin_sources=true
tests=true
documentation=true
```

`App.kt` matches the Kotlin source filter. `src/test/FiltersTest.kt` is excluded
from that filter but matches the test filter. `README.md` matches the
documentation filter. The CLI checks the path strings supplied on the command
line, so these files do not need to exist on disk.

## Matching rules

The Kotlin source filter in `examples/filters.yaml` illustrates the supported syntax:

```yaml
filters:
  kotlin_sources:
    - "**/*.kt"
    - "!**/test/**"
```

- `*` matches within one path segment. `src/*.kt` matches `src/App.kt`.
- `**` matches zero or more path segments. `**/*.kt` matches both `App.kt`
  and `src/main/App.kt`.
- A leading `!` excludes a matching path. Exclusions take precedence for that
  file, regardless of pattern order.

A filter is true when at least one changed path qualifies. If the only change
is `src/test/FiltersTest.kt`, `kotlin_sources=false`. Add `App.kt` to the same
change set and `kotlin_sources=true`. Both outcomes are successful CLI runs.

## Test and build

```sh
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m build
```

The build creates a wheel and a source distribution under `dist/`. The
[GitHub Actions workflow](.github/workflows/ci.yml) runs on Python 3.11 and
3.14. It also installs the wheel in a fresh environment, runs the CLI outside
the source tree, and compares its output with `examples/expected.env.txt`.
That last check verifies that the packaged command works for someone
installing it.

## Design tradeoffs

- **The calling pipeline supplies changed paths.** This keeps the CLI independent
  of Git history and lets each pipeline choose its own comparison, such as a
  pull request against its base branch.
- **The matcher supports a small glob syntax.** Splitting paths at `/` gives
  `*` and `**` explicit behavior. Full `.gitignore` syntax and re-inclusion
  rules are outside the scope of this utility.