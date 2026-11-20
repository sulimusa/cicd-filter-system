# CI/CD Filter System

A Python command-line utility for evaluating changed paths against YAML filters
and producing a dotenv file for CI jobs.

## Development setup

Requires Python 3.11 or newer. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```
