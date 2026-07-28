"""Security and consistency validation for artifact manifests."""
from __future__ import annotations

import ipaddress
import asyncio
import re
import socket
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urlparse

from jsonschema import Draft202012Validator, FormatChecker

from .checksum import validate_checksum


MAX_FILENAME_LENGTH = 255
SAFE_FILENAME = re.compile(r"^[^/\\\x00]+$")
ALLOWED_KINDS = {
    "source", "binary", "patch", "extension", "module", "certificate",
    "script", "archive", "jar", "key", "metadata",
}
ALLOWED_CHANNELS = {
    "recommended", "stable", "mainline", "supported", "legacy", "eol",
    "archive", "unknown",
}
LEGACY_HTTP_HOSTS = {"memcached.org", "www.memcached.org"}
SCHEMA_PATH = Path(__file__).parent / "schema" / "artifacts-v1.schema.json"


def validate_filename(filename: str) -> str:
    """Validate that a filename is a safe, exact basename."""
    value = filename.strip()
    if (
        not value
        or len(value) > MAX_FILENAME_LENGTH
        or value in {".", ".."}
        or ".." in value
        or not SAFE_FILENAME.fullmatch(value)
        or Path(value).name != value
    ):
        raise ValueError("filename must be a safe basename")
    return value


def validate_source_url(url: str, *, allow_legacy_http: bool = True) -> str:
    """Reject unsupported schemes and direct local/private network targets."""
    parsed = urlparse(url.strip())
    allowed_schemes = {"https"}
    if allow_legacy_http:
        allowed_schemes.add("http")
    if parsed.scheme.lower() not in allowed_schemes or not parsed.hostname:
        raise ValueError("source URL must use an allowed HTTP(S) scheme")
    if parsed.username or parsed.password:
        raise ValueError("source URL credentials are not allowed")
    hostname = parsed.hostname.rstrip(".").lower()
    if parsed.scheme.lower() == "http" and hostname not in LEGACY_HTTP_HOSTS:
        raise ValueError("HTTP source host is not in the legacy allowlist")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("local source URL is not allowed")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError("private, loopback, or reserved source URL is not allowed")
    return url.strip()


async def validate_network_target(url: str) -> str:
    """Resolve a source host and reject DNS results in non-public address space."""
    value = validate_source_url(url)
    parsed = urlparse(value)
    hostname = parsed.hostname or ""
    try:
        ipaddress.ip_address(hostname)
        return value
    except ValueError:
        pass
    loop = asyncio.get_running_loop()
    addresses = await loop.getaddrinfo(
        hostname,
        parsed.port or (443 if parsed.scheme == "https" else 80),
        type=socket.SOCK_STREAM,
    )
    if not addresses:
        raise ValueError("source URL hostname did not resolve")
    for address in addresses:
        resolved = ipaddress.ip_address(address[4][0])
        if not resolved.is_global:
            raise ValueError("source URL resolves to private or reserved address space")
    return value


def encoded_mirror_path(filename: str, prefix: str = "/src") -> str:
    """Build a safe public path while preserving the exact filename key."""
    return f"{prefix}/{quote(validate_filename(filename), safe='')}"


def ensure_within_root(path: Path, root: Path) -> Path:
    """Resolve and verify a filesystem path cannot escape the configured root."""
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError("path escapes configured root")
    return resolved_path


def validate_manifest_dict(manifest: dict) -> None:
    """Run cross-field checks not expressible cleanly in JSON Schema."""
    ids: set[str] = set()
    filenames: set[str] = set()
    aliases: set[str] = set()
    recommendation_values = set(manifest.get("version_recommendations", {}).values())
    artifact_versions = {str(item.get("version", "")) for item in manifest.get("artifacts", [])}

    for artifact in manifest.get("artifacts", []):
        artifact_id = artifact["id"]
        filename = validate_filename(artifact["filename"])
        validate_source_url(artifact["source"]["url"])
        if artifact_id in ids:
            raise ValueError(f"duplicate artifact id: {artifact_id}")
        if filename in filenames:
            raise ValueError(f"duplicate artifact filename: {filename}")
        if filename in aliases:
            raise ValueError(f"artifact filename conflicts with alias: {filename}")
        ids.add(artifact_id)
        filenames.add(filename)
        if artifact["mirror"]["path"] != encoded_mirror_path(filename):
            raise ValueError(f"mirror path does not match filename: {filename}")
        for algorithm, digest in artifact.get("checksums", {}).items():
            if not validate_checksum(algorithm, digest):
                raise ValueError(f"invalid {algorithm} checksum for {filename}")
        for alias in artifact.get("aliases", []):
            validate_filename(alias)
            if alias in aliases or alias in filenames:
                raise ValueError(f"conflicting alias: {alias}")
            aliases.add(alias)

    unresolved = sorted(recommendation_values - artifact_versions)
    if unresolved and manifest.get("artifacts"):
        raise ValueError(
            "version recommendations do not resolve to artifacts: "
            + ", ".join(unresolved)
        )


@lru_cache
def _schema_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_manifest_schema(manifest: dict) -> None:
    """Validate the exact published document against the bundled v1 Schema."""
    _schema_validator().validate(manifest)
