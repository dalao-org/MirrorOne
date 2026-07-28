"""Build a stable artifact manifest from a Redis snapshot."""
from __future__ import annotations

import re
import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urlparse

from app import redis_client
from app.services import cache_service

from .checksum import normalize_algorithm, validate_checksum
from .models import (
    Artifact,
    ArtifactManifest,
    ArtifactMirror,
    ArtifactSize,
    ArtifactSource,
    ChecksumMetadata,
    GeneratorInfo,
    ManifestConflict,
    ManifestStatistics,
    MirrorInfo,
    Platform,
)
from .validator import encoded_mirror_path, validate_manifest_dict


COMPOSITE_SOURCES = {"misc", "misc_github", "php_plugins", "php_patches"}
ARCHIVE_SUFFIXES = (
    ".tar.gz", ".tar.xz", ".tar.bz2", ".tar.zst", ".tgz", ".zip", ".gz",
    ".xz", ".bz2", ".jar", ".patch", ".pem",
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _infer_component(filename: str, source: str) -> str:
    if source not in COMPOSITE_SOURCES:
        return source.replace("_", "-")
    stem = filename
    for suffix in ARCHIVE_SUFFIXES:
        if stem.lower().endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    match = re.match(r"(.+?)[-_]v?\d+(?:\.\d+)+(?:[-_].*)?$", stem)
    return (match.group(1) if match else stem).lower().replace("_", "-")


def artifact_id(component: str, version: str, kind: str, platform: Platform) -> str:
    if platform.os == "any" and platform.arch == "any":
        platform_key = "any"
    else:
        parts = [platform.os, platform.arch]
        if platform.libc:
            parts.append(platform.libc)
        platform_key = "-".join(parts)
    return f"{component}:{version}:{kind}:{platform_key}"


def _normalized_checksums(rule: dict) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for raw_algorithm, raw_digest in (rule.get("checksums") or {}).items():
        algorithm = normalize_algorithm(raw_algorithm)
        if algorithm and validate_checksum(algorithm, raw_digest):
            checksums[algorithm] = raw_digest.lower()
    algorithm = normalize_algorithm(rule.get("checksum_type"))
    digest = rule.get("checksum")
    if algorithm and validate_checksum(algorithm, digest):
        checksums[algorithm] = digest.lower()
    return dict(sorted(checksums.items()))


class ManifestBuilder:
    """Create one internally consistent manifest candidate."""

    def __init__(self, settings: dict):
        self.settings = settings

    async def build(
        self,
        *,
        rules: dict[str, dict] | None = None,
        versions: dict[str, str] | None = None,
        conflicts: list[dict] | None = None,
    ) -> ArtifactManifest:
        if rules is None and versions is None and conflicts is None:
            rules, versions, conflicts = await redis_client.get_manifest_snapshot()
        else:
            if rules is None:
                rules = await redis_client.get_all_redirect_rules()
            if versions is None:
                versions = await redis_client.get_all_version_metas()
            if conflicts is None:
                conflicts = await redis_client.get_redirect_conflicts()

        generated_at = utc_now()
        cache_path = cache_service.get_cache_path(self.settings)
        include_cache = self.settings.get("manifest_include_cache_status", True)
        conflict_files = {
            conflict["filename"]
            for conflict in conflicts
            if conflict.get("reason") == "same_filename_different_source_url"
        }
        alias_conflicts = {
            conflict["filename"]
            for conflict in conflicts
            if conflict.get("reason") == "alias_conflict"
        }

        artifacts: list[Artifact] = []
        generated_conflicts = list(conflicts)
        seen_ids: dict[str, str] = {}
        for filename, raw_rule in sorted(rules.items()):
            if filename in conflict_files:
                continue
            rule = {
                "kind": "source",
                "platform": {"os": "any", "arch": "any", "libc": None},
                "channel": "unknown",
                "aliases": [],
                **raw_rule,
            }
            platform = Platform.model_validate(rule["platform"] or {})
            component = rule.get("component") or _infer_component(
                filename,
                rule.get("source", "unknown"),
            )
            kind = rule.get("kind") or "source"
            identifier = artifact_id(component, str(rule.get("version", "")), kind, platform)
            if identifier in seen_ids and seen_ids[identifier] != filename:
                generated_conflicts.append({
                    "filename": filename,
                    "reason": "duplicate_artifact_id",
                    "candidates": [
                        {"filename": seen_ids[identifier], "id": identifier},
                        {"filename": filename, "id": identifier},
                    ],
                })
                continue
            seen_ids[identifier] = filename

            checksums = _normalized_checksums(rule)
            aliases = sorted({
                alias
                for alias in (rule.get("aliases") or [])
                if alias not in alias_conflicts and alias != filename
            })
            cache_info = (
                cache_service.get_cache_info(cache_path, rule.get("source", "unknown"), filename)
                if include_cache
                else None
            )
            cached = bool(cache_info and cache_info["available"])
            if cached:
                integrity_status = cache_info.get("integrity_status")
                if not integrity_status:
                    integrity_status = (
                        "verified_upstream_checksum"
                        if checksums
                        else "unverified_upstream_checksum_unavailable"
                    )
            else:
                integrity_status = "not_cached"

            if checksums:
                strength = (
                    "strong"
                    if any(name in checksums for name in ("sha512", "sha384", "sha256"))
                    else "legacy"
                )
                checksum_metadata = ChecksumMetadata(
                    available=True,
                    provenance="upstream",
                    source_url=rule.get("checksum_source_url"),
                    strength=strength,
                )
            else:
                checksum_metadata = ChecksumMetadata(
                    available=False,
                    provenance="none",
                    source_url=None,
                    strength="none",
                    reason=rule.get("checksum_unavailable_reason")
                    or "upstream_not_published",
                )

            updated_at = rule.get("updated_at") or generated_at
            source_url = rule["url"]
            artifact = Artifact(
                id=identifier,
                component=component,
                version=str(rule.get("version", "")),
                channel=rule.get("channel") or "unknown",
                kind=kind,
                filename=filename,
                aliases=aliases,
                platform=platform,
                source=ArtifactSource(
                    provider=urlparse(source_url).hostname or rule.get("source", "unknown"),
                    url=source_url,
                    discovered_at=updated_at,
                ),
                mirror=ArtifactMirror(
                    path=encoded_mirror_path(filename),
                    legacy_path=encoded_mirror_path(filename, "/oneinstack/src"),
                    available=True,
                    cache_status="cached" if cached else "not_cached",
                    cached_at=cache_info.get("cached_at") if cache_info else None,
                    integrity_status=integrity_status,
                ),
                checksums=checksums,
                checksum_metadata=checksum_metadata,
                size=ArtifactSize(
                    bytes=cache_info.get("size_bytes") if cache_info else None,
                    source="download" if cache_info else "unknown",
                ),
                updated_at=updated_at,
            )
            artifacts.append(artifact)

        artifacts.sort(
            key=lambda item: (
                item.component,
                item.version,
                item.kind,
                item.platform.arch,
                item.filename,
            )
        )
        conflicts_models = [
            ManifestConflict(
                filename=conflict["filename"],
                reason=conflict["reason"],
                candidates=[
                    {
                        key: value
                        for key, value in candidate.items()
                        if key != "updated_at"
                    }
                    for candidate in conflict.get("candidates", [])
                ],
            )
            for conflict in sorted(
                generated_conflicts,
                key=lambda item: (item.get("filename", ""), item.get("reason", "")),
            )
        ]
        with_checksum = sum(bool(item.checksums) for item in artifacts)
        cached_count = sum(item.mirror.cache_status == "cached" for item in artifacts)
        commit = str(self.settings.get("manifest_generator_commit") or "unknown")[:12]
        manifest = ArtifactManifest(
            **{
                "$schema": "/manifests/schema/artifacts-v1.schema.json",
                "manifest_revision": f"{generated_at}-{commit[:7]}",
                "generated_at": generated_at,
                "generator": GeneratorInfo(
                    version=str(self.settings.get("app_version", "2.1.0")),
                    commit=commit,
                    instance_id=str(self.settings.get("manifest_instance_id", "mirrorone")),
                ),
                "mirror": MirrorInfo(
                    base_url=str(
                        self.settings.get("manifest_public_base_url")
                        or "http://localhost:3000"
                    ).rstrip("/"),
                    current_mode=str(self.settings.get("mirror_type", "redirect")),
                ),
                "version_recommendations": dict(sorted(versions.items())),
                "artifacts": artifacts,
                "conflicts": conflicts_models,
                "statistics": ManifestStatistics(
                    artifact_count=len(artifacts),
                    with_upstream_checksum=with_checksum,
                    without_upstream_checksum=len(artifacts) - with_checksum,
                    cached=cached_count,
                    not_cached=len(artifacts) - cached_count,
                    conflict_count=len(conflicts_models),
                ),
            }
        )
        semantic = manifest.model_dump(by_alias=True)
        semantic.pop("generated_at", None)
        semantic.pop("manifest_revision", None)
        content_fingerprint = hashlib.sha256(
            json.dumps(
                semantic,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:8]
        manifest.manifest_revision = (
            f"{generated_at}-{commit[:7]}-{content_fingerprint}"
        )
        validate_manifest_dict(manifest.model_dump(by_alias=True))
        return manifest
