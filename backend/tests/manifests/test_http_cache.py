from pathlib import Path

from app.routers.manifests import (
    _cached_file_headers,
    _file_headers,
    _not_modified,
)
from starlette.requests import Request


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


def test_file_headers_cache_payload_digest(monkeypatch, tmp_path: Path):
    path = tmp_path / "artifacts.json"
    path.write_text('{"manifest_revision":"revision"}\n', encoding="utf-8")
    real_read_bytes = Path.read_bytes
    reads = 0

    def counted_read_bytes(candidate):
        nonlocal reads
        if candidate == path:
            reads += 1
        return real_read_bytes(candidate)

    _cached_file_headers.cache_clear()
    monkeypatch.setattr(Path, "read_bytes", counted_read_bytes)
    first = _file_headers(path)
    second = _file_headers(path)
    assert first == second
    assert reads == 1
