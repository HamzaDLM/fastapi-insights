# Release Process

This project publishes through GitHub Actions using PyPI Trusted Publishing.

## One-time setup

### TestPyPI Trusted Publisher

In TestPyPI, configure a Trusted Publisher for:

- Owner: your GitHub account or org
- Repository: `fastapi-insights`
- Workflow: `.github/workflows/release.yml`
- Environment: `testpypi`

### PyPI Trusted Publisher

In PyPI, configure a Trusted Publisher for:

- Owner: your GitHub account or org
- Repository: `fastapi-insights`
- Workflow: `.github/workflows/release.yml`
- Environment: `pypi`

## Before releasing

1. Confirm the package version in [pyproject.toml](pyproject.toml).
2. Run:

```bash
uv sync --dev
uv run pytest
```

3. Review the working tree and commit only the intended release changes.
4. Push the branch and let CI pass.

## Publish to TestPyPI first

From GitHub Actions, run the `Publish` workflow with:

- `target`: `testpypi`
- `ref`: the tag or commit SHA you want to publish

After it succeeds, verify the TestPyPI release:

```bash
python -m venv /tmp/fastapi-insights-testpypi
/tmp/fastapi-insights-testpypi/bin/pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple fastapi-insights
```

Then smoke-test a minimal FastAPI app and confirm the dashboard assets are present.

## Publish to PyPI

After validating the TestPyPI release, run the same `Publish` workflow with:

- `target`: `pypi`
- `ref`: the exact same tag or commit SHA that was published to TestPyPI

## Recommended tagging flow

1. Bump version in `pyproject.toml`.
2. Commit the release changes.
3. Create an annotated tag such as:

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

4. Use `v0.1.0` as the `ref` input when running the `Publish` workflow.
