import httpx
import pytest
from fastapi import FastAPI

from app import redis_client
from app.manifests.builder import ManifestBuilder
from app.manifests.publisher import ManifestPublisher
from app.routers.manifests import router as manifests_router
from app.routers.redirect import router as redirect_router
from app.routers import manifests as manifests_module
from app.routers import redirect as redirect_module
from app.manifests import service as manifest_service
from tests.manifests.test_redis_metadata import FakeRedis


@pytest.mark.asyncio
async def test_redis_to_manifest_to_http_and_legacy_contract(
    monkeypatch,
    tmp_path,
):
    fake = FakeRedis()

    async def get_fake():
        return fake

    async def mirror_settings():
        return {"mirror_type": "redirect", "cache_path": str(tmp_path / "cache")}

    monkeypatch.setattr(redis_client, "get_redis", get_fake)
    monkeypatch.setattr(redirect_module, "get_mirror_settings", mirror_settings)
    await redis_client.set_redirect_rule(
        filename="php-8.4.12.tar.gz",
        url="https://example.com/php-8.4.12.tar.gz",
        version="8.4.12",
        source="php",
        checksum="a" * 64,
        checksum_type="sha256",
    )
    await redis_client.set_version_meta("php84_ver", "8.4.12")
    settings = {
        "cache_path": str(tmp_path / "cache"),
        "mirror_type": "redirect",
        "manifest_public_base_url": "https://mirror.example.com",
        "manifest_generator_commit": "abcdef0",
        "manifest_instance_id": "integration",
    }
    manifest = await ManifestBuilder(settings).build()
    publisher = ManifestPublisher(tmp_path / "manifests")
    publisher.publish(manifest)
    monkeypatch.setattr(manifests_module, "get_publisher", lambda: publisher)
    monkeypatch.setattr(manifest_service, "get_publisher", lambda settings=None: publisher)

    app = FastAPI()
    app.include_router(manifests_router)
    app.include_router(redirect_router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://mirror.example.com",
        follow_redirects=False,
    ) as client:
        response = await client.get("/manifests/artifacts.json")
        assert response.status_code == 200
        document = response.json()
        assert document["artifacts"][0]["checksums"] == {"sha256": "a" * 64}
        assert (await client.get(
            "/manifests/artifacts.json",
            headers={"If-None-Match": response.headers["etag"]},
        )).status_code == 304
        sidecar = await client.get("/manifests/artifacts.json.sha256")
        assert sidecar.status_code == 200
        assert sidecar.text.endswith("  artifacts.json\n")
        assert (await client.get(
            "/src/php-8.4.12.tar.gz",
        )).status_code == 301
        assert (await client.get(
            "/src/php-8.4.12.tar.gz?force_redirect=true",
        )).status_code == 302
        assert (await client.get(
            "/oneinstack/src/php-8.4.12.tar.gz",
        )).status_code == 301
        assert (await client.get(
            "/suggest_versions.txt",
        )).text == "php84_ver=8.4.12"
        legacy_resource = (await client.get("/resource.json")).json()
        assert legacy_resource["sources"]["php"][0] == {
            "file": "php-8.4.12.tar.gz",
            "url": "https://example.com/php-8.4.12.tar.gz",
            "version": "8.4.12",
        }
