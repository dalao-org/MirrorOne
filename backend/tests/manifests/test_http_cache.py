from pathlib import Path

from starlette.requests import Request

from app.routers.manifests import _file_headers, _not_modified


def request_with_headers(headers: dict[str, str]) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in headers.items()
    ]
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/manifests/artifacts.json",
        "headers": raw_headers,
    })


def test_if_none_match_and_if_modified_since(tmp_path: Path):
    path = tmp_path / "artifacts.json"
    path.write_text('{"manifest_revision":"revision"}\n', encoding="utf-8")
    headers = _file_headers(path, schema_version=True)
    assert _not_modified(
        request_with_headers({"If-None-Match": headers["ETag"]}),
        path,
        headers,
    )
    assert _not_modified(
        request_with_headers({"If-Modified-Since": headers["Last-Modified"]}),
        path,
        headers,
    )
    assert not _not_modified(
        request_with_headers({"If-None-Match": '"other"'}),
        path,
        headers,
    )
    assert not _not_modified(
        request_with_headers({
            "If-None-Match": '"other"',
            "If-Modified-Since": headers["Last-Modified"],
        }),
        path,
        headers,
    )
