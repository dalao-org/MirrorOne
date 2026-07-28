from pathlib import Path

import pytest
from pydantic import ValidationError

from app.manifests.publisher import ManifestPublisher


def manifest_document() -> dict:
    return {
        "$schema": "/manifests/schema/artifacts-v1.schema.json",
        "schema_name": "mirrorone-artifacts",
        "schema_version": 1,
        "manifest_revision": "2026-07-28T08:00:00Z-abcdef0",
        "generated_at": "2026-07-28T08:00:00Z",
        "generator": {
            "name": "MirrorOne", "version": "2.1.0",
            "commit": "abcdef0", "instance_id": "test",
        },
        "mirror": {
            "base_url": "https://mirror.example.com",
            "download_path_template": "/src/{filename}",
            "legacy_path_template": "/oneinstack/src/{filename}",
            "force_redirect_parameter": "force_redirect=true",
            "supported_modes": ["redirect", "cache"],
            "current_mode": "redirect",
        },
        "checksum_policy": {
            "source": "upstream", "checksum_optional": True,
            "missing_checksum_allowed": True,
            "mirror_computed_digest_is_authoritative": False,
            "preferred_algorithms": ["sha512", "sha384", "sha256", "sha1", "md5"],
        },
        "version_recommendations": {},
        "artifacts": [],
        "conflicts": [],
        "statistics": {
            "artifact_count": 0, "with_upstream_checksum": 0,
            "without_upstream_checksum": 0, "cached": 0,
            "not_cached": 0, "conflict_count": 0,
        },
    }


def test_atomic_publish_sidecar_history_and_stable_bytes(tmp_path: Path):
    publisher = ManifestPublisher(tmp_path, keep_history=2)
    first = publisher.publish(manifest_document())
    first_bytes = publisher.manifest_path.read_bytes()
    repeated = manifest_document()
    repeated["generated_at"] = "2026-07-28T09:00:00Z"
    repeated["manifest_revision"] = "2026-07-28T09:00:00Z-abcdef0"
    second = publisher.publish(repeated)
    assert first["changed"] is True
    assert second["changed"] is False
    assert publisher.manifest_path.read_bytes() == first_bytes
    assert publisher.sidecar_path.read_text().endswith("  artifacts.json\n")
    assert len(list((tmp_path / "history").glob("artifacts-*.json"))) == 1


def test_failed_candidate_keeps_last_known_good(tmp_path: Path):
    publisher = ManifestPublisher(tmp_path)
    publisher.publish(manifest_document())
    previous = publisher.manifest_path.read_bytes()
    invalid = manifest_document()
    invalid["schema_version"] = 2
    with pytest.raises(ValidationError):
        publisher.publish(invalid)
    assert publisher.manifest_path.read_bytes() == previous


def test_sidecar_replace_failure_rolls_back_public_pair(monkeypatch, tmp_path: Path):
    publisher = ManifestPublisher(tmp_path)
    publisher.publish(manifest_document())
    previous_manifest = publisher.manifest_path.read_bytes()
    previous_sidecar = publisher.sidecar_path.read_bytes()
    changed = manifest_document()
    changed["mirror"]["current_mode"] = "cache"
    changed["manifest_revision"] = "2026-07-28T10:00:00Z-abcdef0"
    changed["generated_at"] = "2026-07-28T10:00:00Z"

    import app.manifests.publisher as publisher_module
    real_replace = publisher_module.os.replace
    failed_once = False

    def fail_sidecar_once(source, destination):
        nonlocal failed_once
        if str(destination).endswith("artifacts.json.sha256") and not failed_once:
            failed_once = True
            raise OSError("injected sidecar failure")
        return real_replace(source, destination)

    monkeypatch.setattr(publisher_module.os, "replace", fail_sidecar_once)
    with pytest.raises(OSError, match="injected"):
        publisher.publish(changed)
    assert publisher.manifest_path.read_bytes() == previous_manifest
    assert publisher.sidecar_path.read_bytes() == previous_sidecar
