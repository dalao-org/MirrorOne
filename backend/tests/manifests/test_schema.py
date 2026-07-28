import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "manifests"
    / "schema"
    / "artifacts-v1.schema.json"
)


def base_artifact(filename: str, version: str = "1.0.0") -> dict:
    return {
        "id": f"sample-{filename}:{version}:source:any",
        "component": f"sample-{filename}",
        "version": version,
        "channel": "stable",
        "kind": "source",
        "filename": filename,
        "aliases": [],
        "platform": {"os": "any", "arch": "any", "libc": None},
        "source": {
            "provider": "example.com",
            "url": f"https://example.com/{filename}",
            "discovered_at": "2026-07-28T08:00:00Z"
        },
        "mirror": {
            "path": f"/src/{filename}",
            "legacy_path": f"/oneinstack/src/{filename}",
            "available": True,
            "cache_status": "not_cached",
            "cached_at": None,
            "integrity_status": "not_cached"
        },
        "checksums": {},
        "checksum_metadata": {
            "available": False,
            "provenance": "none",
            "source_url": None,
            "strength": "none",
            "reason": "upstream_not_published"
        },
        "size": {"bytes": None, "source": "unknown"},
        "updated_at": "2026-07-28T08:00:00Z"
    }


def test_required_schema_samples():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    artifacts = []

    sha = base_artifact("sha256-1.0.0.tar.gz")
    sha["checksums"] = {"sha256": "a" * 64}
    sha["checksum_metadata"] = {
        "available": True, "provenance": "upstream",
        "source_url": "https://example.com/checksums", "strength": "strong",
        "reason": None,
    }
    artifacts.append(sha)

    md5 = base_artifact("md5-1.0.0.tar.gz")
    md5["checksums"] = {"md5": "b" * 32}
    md5["checksum_metadata"] = {
        "available": True, "provenance": "upstream",
        "source_url": None, "strength": "legacy", "reason": None,
    }
    artifacts.append(md5)
    artifacts.append(base_artifact("no-checksum-1.0.0.tar.gz"))

    binary = base_artifact("mysql-8.4.6-linux-glibc2.28-x86_64.tar.xz", "8.4.6")
    binary["kind"] = "binary"
    binary["platform"] = {"os": "linux", "arch": "x86_64", "libc": "glibc2.28"}
    artifacts.append(binary)

    patch = base_artifact("fpm-race-condition.patch")
    patch["kind"] = "patch"
    artifacts.append(patch)

    alias = base_artifact("canonical-1.0.0.tar.gz")
    alias["aliases"] = ["legacy-name.tar.gz"]
    artifacts.append(alias)

    cached = base_artifact("cached-1.0.0.tar.gz")
    cached["mirror"].update({
        "cache_status": "cached",
        "cached_at": "2026-07-28T08:03:10Z",
        "integrity_status": "unverified_upstream_checksum_unavailable",
    })
    cached["size"] = {"bytes": 123, "source": "download"}
    artifacts.append(cached)

    legacy = base_artifact("legacy-1.0.0.tar.gz")
    legacy["channel"] = "eol"
    artifacts.append(legacy)

    manifest = {
        "$schema": "/manifests/schema/artifacts-v1.schema.json",
        "schema_name": "mirrorone-artifacts",
        "schema_version": 1,
        "manifest_revision": "2026-07-28T08:15:30Z-abcdef0",
        "generated_at": "2026-07-28T08:15:30Z",
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
            "current_mode": "cache",
        },
        "checksum_policy": {
            "source": "upstream",
            "checksum_optional": True,
            "missing_checksum_allowed": True,
            "mirror_computed_digest_is_authoritative": False,
            "preferred_algorithms": ["sha512", "sha384", "sha256", "sha1", "md5"],
        },
        "version_recommendations": {},
        "artifacts": artifacts,
        "conflicts": [],
        "statistics": {
            "artifact_count": len(artifacts),
            "with_upstream_checksum": 2,
            "without_upstream_checksum": len(artifacts) - 2,
            "cached": 1,
            "not_cached": len(artifacts) - 1,
            "conflict_count": 0,
        },
    }
    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(manifest)
