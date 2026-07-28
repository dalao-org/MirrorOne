"""Pydantic domain models for the version 1 artifact manifest."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .checksum import validate_checksum
from .validator import ALLOWED_CHANNELS, ALLOWED_KINDS, validate_filename, validate_source_url


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Platform(StrictModel):
    os: str = "any"
    arch: str = "any"
    libc: str | None = None


class ArtifactSource(StrictModel):
    provider: str
    url: str
    discovered_at: str

    @model_validator(mode="after")
    def validate_url(self) -> "ArtifactSource":
        validate_source_url(self.url)
        return self


class ArtifactMirror(StrictModel):
    path: str
    legacy_path: str
    available: bool
    cache_status: Literal["cached", "not_cached", "quarantined"]
    cached_at: str | None = None
    integrity_status: Literal[
        "verified_upstream_checksum",
        "unverified_upstream_checksum_unavailable",
        "checksum_mismatch",
        "not_cached",
    ] = "not_cached"


class ChecksumMetadata(StrictModel):
    available: bool
    provenance: Literal["upstream", "none"]
    source_url: str | None = None
    strength: Literal["strong", "legacy", "none"]
    reason: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> ChecksumMetadata:
        if self.source_url:
            validate_source_url(self.source_url)
        return self


class ArtifactSize(StrictModel):
    bytes: int | None = Field(default=None, ge=0)
    source: Literal["download", "unknown"]


class Artifact(StrictModel):
    id: str
    component: str
    version: str
    channel: str = "unknown"
    kind: str = "source"
    filename: str
    aliases: list[str] = Field(default_factory=list)
    platform: Platform = Field(default_factory=Platform)
    source: ArtifactSource
    mirror: ArtifactMirror
    checksums: dict[str, str] = Field(default_factory=dict)
    checksum_metadata: ChecksumMetadata
    size: ArtifactSize = Field(default_factory=lambda: ArtifactSize(source="unknown"))
    updated_at: str

    @model_validator(mode="after")
    def validate_artifact(self) -> "Artifact":
        validate_filename(self.filename)
        if self.kind not in ALLOWED_KINDS:
            raise ValueError(f"unsupported artifact kind: {self.kind}")
        if self.channel not in ALLOWED_CHANNELS:
            raise ValueError(f"unsupported artifact channel: {self.channel}")
        for algorithm, digest in self.checksums.items():
            if not validate_checksum(algorithm, digest):
                raise ValueError(f"invalid checksum: {algorithm}")
        return self


class GeneratorInfo(StrictModel):
    name: str = "MirrorOne"
    version: str
    commit: str
    instance_id: str


class MirrorInfo(StrictModel):
    base_url: str
    download_path_template: str = "/src/{filename}"
    legacy_path_template: str = "/oneinstack/src/{filename}"
    force_redirect_parameter: str = "force_redirect=true"
    supported_modes: list[Literal["redirect", "cache"]] = Field(
        default_factory=lambda: ["redirect", "cache"]
    )
    current_mode: Literal["redirect", "cache"]


class ChecksumPolicy(StrictModel):
    source: str = "upstream"
    checksum_optional: bool = True
    missing_checksum_allowed: bool = True
    mirror_computed_digest_is_authoritative: bool = False
    preferred_algorithms: list[str] = Field(
        default_factory=lambda: ["sha512", "sha384", "sha256", "sha1", "md5"]
    )


class ManifestConflict(StrictModel):
    filename: str
    reason: str
    candidates: list[dict]


class ManifestStatistics(StrictModel):
    artifact_count: int = 0
    with_upstream_checksum: int = 0
    without_upstream_checksum: int = 0
    cached: int = 0
    not_cached: int = 0
    conflict_count: int = 0


class ArtifactManifest(StrictModel):
    schema_: str = Field(alias="$schema")
    schema_name: Literal["mirrorone-artifacts"] = "mirrorone-artifacts"
    schema_version: Literal[1] = 1
    manifest_revision: str
    generated_at: str
    generator: GeneratorInfo
    mirror: MirrorInfo
    checksum_policy: ChecksumPolicy = Field(default_factory=ChecksumPolicy)
    version_recommendations: dict[str, str] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    conflicts: list[ManifestConflict] = Field(default_factory=list)
    statistics: ManifestStatistics = Field(default_factory=ManifestStatistics)
