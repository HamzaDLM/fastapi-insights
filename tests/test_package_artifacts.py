from pathlib import Path


def test_package_sources_manifest_lists_static_assets() -> None:
    sources_manifest = Path("fastapi_insights.egg-info/SOURCES.txt")
    assert sources_manifest.exists()

    file_names = set(sources_manifest.read_text().splitlines())

    assert "fastapi_insights/static/frontend/index.html" in file_names
    assert "fastapi_insights/static/frontend/main.js" in file_names
    assert "fastapi_insights/static/frontend/favicon.ico" in file_names
    assert "fastapi_insights/static/bg.png" in file_names
    assert "fastapi_insights/py.typed" in file_names


def test_package_metadata_has_expected_name_and_version() -> None:
    package_metadata = Path("fastapi_insights.egg-info/PKG-INFO").read_text()
    assert "Name: fastapi-insights" in package_metadata
    assert "Version: 0.1.0" in package_metadata
