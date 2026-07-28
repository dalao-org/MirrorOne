import hashlib
from pathlib import Path

import httpx
import pytest

from app.services.cache_service import download_file, download_resource


@pytest.mark.asyncio
async def test_checksum_mismatch_is_quarantined_and_does_not_replace_cache(
    monkeypatch,
    tmp_path: Path,
):
    async def ignore_event(*args, **kwargs):
        return None

    monkeypatch.setattr("app.redis_client.record_manifest_event", ignore_event)
    async def allow_target(url):
        return url
    monkeypatch.setattr(
        "app.services.cache_service.validate_network_target",
        allow_target,
    )
    source_dir = tmp_path / "php"
    source_dir.mkdir()
    destination = source_dir / "php-1.0.0.tar.gz"
    destination.write_bytes(b"known-good")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, stream=httpx.ByteStream(b"tampered"))
    )
    async with httpx.AsyncClient(transport=transport) as client:
        result = await download_file(
            client,
            "https://example.com/php-1.0.0.tar.gz?secret=redacted",
            destination,
            checksums={"sha256": hashlib.sha256(b"expected").hexdigest()},
        )
    assert result is False
    assert destination.read_bytes() == b"known-good"
    quarantined = list((tmp_path / "quarantine" / "php").glob("*checksum_mismatch*"))
    assert quarantined


@pytest.mark.asyncio
async def test_missing_upstream_checksum_is_cached_as_unverified(
    monkeypatch,
    tmp_path: Path,
):
    async def allow_target(url):
        return url

    monkeypatch.setattr(
        "app.services.cache_service.validate_network_target",
        allow_target,
    )
    source_dir = tmp_path / "nginx"
    source_dir.mkdir()
    destination = source_dir / "nginx-1.0.0.tar.gz"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, stream=httpx.ByteStream(b"payload"))
    )
    async with httpx.AsyncClient(transport=transport) as client:
        result = await download_file(
            client,
            "https://example.com/nginx-1.0.0.tar.gz",
            destination,
            checksums={},
        )
    assert result is True
    metadata = (
        source_dir / ".metadata" / "nginx-1.0.0.tar.gz.json"
    ).read_text(encoding="utf-8")
    assert "unverified_upstream_checksum_unavailable" in metadata
    assert "observed_digests" in metadata


@pytest.mark.asyncio
async def test_observed_digest_detects_corruption_without_upstream_checksum(
    monkeypatch,
    tmp_path: Path,
):
    async def allow_target(url):
        return url

    async def ignore_event(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.cache_service.validate_network_target",
        allow_target,
    )
    monkeypatch.setattr("app.redis_client.record_manifest_event", ignore_event)
    destination = tmp_path / "nginx" / "nginx-1.0.0.tar.gz"
    destination.parent.mkdir()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, stream=httpx.ByteStream(b"original"))
    )
    async with httpx.AsyncClient(transport=transport) as client:
        assert await download_file(
            client,
            "https://example.com/nginx-1.0.0.tar.gz",
            destination,
            checksums={},
        )
        destination.write_bytes(b"corrupted")
        assert not await download_resource(
            client,
            "https://example.com/nginx-1.0.0.tar.gz",
            destination.name,
            "nginx",
            tmp_path,
            skip_existing=True,
            checksums={},
        )
    assert not destination.exists()
    assert list((tmp_path / "quarantine" / "nginx").glob("*observed_digest_changed*"))


@pytest.mark.asyncio
async def test_every_redirect_target_is_validated_before_request(
    monkeypatch,
    tmp_path: Path,
):
    validated = []

    async def validate_target(url):
        validated.append(url)
        if "127.0.0.1" in url:
            raise ValueError("private target")
        return url

    monkeypatch.setattr(
        "app.services.cache_service.validate_network_target",
        validate_target,
    )

    def handler(request):
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/file"})
        raise AssertionError("private redirect target must not be requested")

    destination = tmp_path / "sample" / "file.tar.gz"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert not await download_file(
            client,
            "https://example.com/file.tar.gz",
            destination,
        )
    assert validated == [
        "https://example.com/file.tar.gz",
        "http://127.0.0.1/file",
    ]
    assert not destination.exists()
