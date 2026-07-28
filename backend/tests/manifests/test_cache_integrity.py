import hashlib
from pathlib import Path

import httpx
import pytest
from app.manifests.validator import ValidatedNetworkTarget
from app.services import cache_service
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


@pytest.mark.asyncio
async def test_download_connects_to_the_validated_address_with_original_host(
    monkeypatch,
    tmp_path: Path,
):
    async def pin_target(url):
        return ValidatedNetworkTarget(url, "example.com", ("203.0.113.10",))

    monkeypatch.setattr(
        "app.services.cache_service.validate_network_target",
        pin_target,
    )

    def handler(request):
        assert request.url.host == "203.0.113.10"
        assert request.headers["host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(200, stream=httpx.ByteStream(b"payload"))

    destination = tmp_path / "sample" / "file.tar.gz"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await download_file(
            client,
            "https://example.com/file.tar.gz",
            destination,
        )


def test_find_cached_file_skips_path_that_resolves_outside_root(
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "source"
    source.mkdir()
    (source / "file.tar.gz").write_bytes(b"payload")

    def reject_path(path, root):
        raise ValueError("path escapes configured root")

    monkeypatch.setattr(cache_service, "ensure_within_root", reject_path)
    assert cache_service.find_cached_file(tmp_path, "file.tar.gz") is None


def test_cached_file_lookup_rejects_legacy_unsafe_source(tmp_path: Path):
    assert cache_service.get_cached_file_path(
        tmp_path,
        "../legacy",
        "file.tar.gz",
    ) is None


@pytest.mark.asyncio
async def test_download_resource_rejects_unsafe_source(tmp_path: Path):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(500)
        )
    ) as client:
        assert not await download_resource(
            client,
            "https://example.com/file.tar.gz",
            "file.tar.gz",
            "../unsafe",
            tmp_path,
        )


@pytest.mark.asyncio
async def test_unchanged_recent_cache_entry_skips_deep_hash(
    monkeypatch,
    tmp_path: Path,
):
    payload = b"payload"

    async def allow_target(url):
        return url

    monkeypatch.setattr(cache_service, "validate_network_target", allow_target)
    destination = tmp_path / "sample" / "file.tar.gz"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, stream=httpx.ByteStream(payload))
    )
    async with httpx.AsyncClient(transport=transport) as client:
        assert await download_file(
            client,
            "https://example.com/file.tar.gz",
            destination,
            checksums={"sha256": hashlib.sha256(payload).hexdigest()},
        )

        def unexpected_digest(*args, **kwargs):
            raise AssertionError("unchanged recent file should not be re-hashed")

        monkeypatch.setattr(cache_service, "digest_file", unexpected_digest)
        assert await download_resource(
            client,
            "https://example.com/file.tar.gz",
            destination.name,
            "sample",
            tmp_path,
            checksums={"SHA-256": hashlib.sha256(payload).hexdigest()},
        )


@pytest.mark.asyncio
async def test_parallel_download_normalizes_checksum_algorithm_alias(
    monkeypatch,
    tmp_path: Path,
):
    payload = b"payload"
    captured = {}

    async def capture_download(client, url, dest_path, checksums=None, **kwargs):
        captured.update(checksums or {})
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(payload)
        return True

    monkeypatch.setattr(cache_service, "download_file", capture_download)
    stats = await cache_service.download_resources_parallel(
        resources=[{
            "url": "https://example.com/file.tar.gz",
            "file_name": "file.tar.gz",
            "source": "sample",
            "checksum": hashlib.sha256(payload).hexdigest(),
            "checksum_type": "SHA-256SUM",
        }],
        cache_path=tmp_path,
    )
    assert stats == {"downloaded": 1, "skipped": 0, "failed": 0}
    assert captured == {"sha256": hashlib.sha256(payload).hexdigest()}
