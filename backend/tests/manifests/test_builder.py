import pytest

from app.manifests.builder import ManifestBuilder


@pytest.mark.asyncio
async def test_builder_supports_old_redis_data_and_stable_sort(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.manifests.builder.cache_service.get_cache_info",
        lambda *args: None,
    )
    rules = {
        "php-8.4.12.tar.gz": {
            "url": "https://www.php.net/distributions/php-8.4.12.tar.gz",
            "version": "8.4.12",
            "source": "php",
            "checksum": "a" * 64,
            "checksum_type": "SHA-256",
            "updated_at": "2026-07-28T08:00:00Z",
        },
        "nginx-1.28.0.tar.gz": {
            "url": "https://nginx.org/download/nginx-1.28.0.tar.gz",
            "version": "1.28.0",
            "source": "nginx",
            "updated_at": "2026-07-28T07:00:00Z",
        },
    }
    builder = ManifestBuilder({
        "cache_path": str(tmp_path),
        "mirror_type": "cache",
        "manifest_public_base_url": "https://mirror.example.com",
        "manifest_generator_commit": "abcdef0",
        "manifest_instance_id": "test",
    })
    manifest = await builder.build(
        rules=rules,
        versions={"php84_ver": "8.4.12", "nginx_ver": "1.28.0"},
        conflicts=[],
    )
    assert [item.filename for item in manifest.artifacts] == [
        "nginx-1.28.0.tar.gz",
        "php-8.4.12.tar.gz",
    ]
    assert manifest.artifacts[0].checksums == {}
    assert manifest.artifacts[1].checksums == {"sha256": "a" * 64}


@pytest.mark.asyncio
async def test_conflicted_filename_is_reported_and_not_published(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.manifests.builder.cache_service.get_cache_info",
        lambda *args: None,
    )
    filename = "same-1.0.0.tar.gz"
    manifest = await ManifestBuilder({
        "cache_path": str(tmp_path),
        "manifest_generator_commit": "abcdef0",
    }).build(
        rules={
            filename: {
                "url": f"https://one.example/{filename}",
                "version": "1.0.0",
                "source": "same",
                "updated_at": "2026-07-28T08:00:00Z",
            }
        },
        versions={},
        conflicts=[{
            "filename": filename,
            "reason": "same_filename_different_source_url",
            "candidates": [
                {"url": f"https://one.example/{filename}"},
                {"url": f"https://two.example/{filename}"},
            ],
        }],
    )
    assert manifest.artifacts == []
    assert manifest.conflicts[0].filename == filename
