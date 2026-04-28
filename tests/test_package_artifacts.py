from pathlib import Path


def test_manifest_includes_required_package_assets() -> None:
    manifest = Path("MANIFEST.in").read_text()

    assert "recursive-include fastapi_insights/static *" in manifest
    assert "include fastapi_insights/py.typed" in manifest


def test_pyproject_has_expected_package_metadata() -> None:
    pyproject = Path("pyproject.toml").read_text()

    assert 'name = "fastapi-insights"' in pyproject
    assert 'readme = "README.md"' in pyproject
