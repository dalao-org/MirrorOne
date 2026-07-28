"""Checksum normalization and digest helpers."""
from __future__ import annotations

import hashlib
import hmac
from pathlib import Path


ALGORITHM_LENGTHS = {
    "md5": 32,
    "sha1": 40,
    "sha256": 64,
    "sha384": 96,
    "sha512": 128,
}

_ALIASES = {
    "md5": "md5",
    "md5sum": "md5",
    "sha1": "sha1",
    "sha1sum": "sha1",
    "sha256": "sha256",
    "sha256sum": "sha256",
    "sha384": "sha384",
    "sha384sum": "sha384",
    "sha512": "sha512",
    "sha512sum": "sha512",
}

PREFERRED_ALGORITHMS = ("sha512", "sha384", "sha256", "sha1", "md5")


def normalize_algorithm(value: str | None) -> str | None:
    """Convert common checksum algorithm spellings to the manifest spelling."""
    if not value:
        return None
    compact = value.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    return _ALIASES.get(compact)


def validate_checksum(algorithm: str, digest: str | None) -> bool:
    """Return whether a digest is valid hexadecimal with the required length."""
    normalized = normalize_algorithm(algorithm)
    if normalized is None or not digest:
        return False
    value = digest.strip()
    if len(value) != ALGORITHM_LENGTHS[normalized]:
        return False
    return all(character in "0123456789abcdefABCDEF" for character in value)


def choose_strongest(checksums: dict[str, str]) -> tuple[str, str] | None:
    """Choose the strongest supported checksum."""
    for algorithm in PREFERRED_ALGORITHMS:
        digest = checksums.get(algorithm)
        if digest and validate_checksum(algorithm, digest):
            return algorithm, digest.strip().lower()
    return None


def digest_file(path: Path, algorithm: str) -> str:
    """Calculate a hexadecimal digest without loading the whole file."""
    normalized = normalize_algorithm(algorithm)
    if normalized is None:
        raise ValueError(f"Unsupported checksum algorithm: {algorithm}")
    digest = hashlib.new(normalized, usedforsecurity=False)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digests_equal(actual: str, expected: str) -> bool:
    """Compare digests in constant time."""
    return hmac.compare_digest(actual.lower(), expected.lower())
