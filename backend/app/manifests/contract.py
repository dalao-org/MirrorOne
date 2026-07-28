"""LNMP compatibility contract validation."""
from __future__ import annotations

import fnmatch
from collections import Counter

from .checksum import validate_checksum
from .validator import encoded_mirror_path


def validate_lnmp_contract(manifest: dict, fixture: dict) -> dict:
    """Return a complete compatibility report rather than failing at the first item."""
    artifacts = manifest.get("artifacts", [])
    filenames = {artifact.get("filename") for artifact in artifacts}
    aliases = {
        alias
        for artifact in artifacts
        for alias in artifact.get("aliases", [])
    }
    available = filenames | aliases
    missing_patterns = [
        pattern
        for pattern in fixture.get("required_filenames", [])
        if not any(fnmatch.fnmatch(filename or "", pattern) for filename in available)
    ]
    id_counts = Counter(artifact.get("id") for artifact in artifacts)
    duplicate_ids = sorted(
        (
            artifact_id
            for artifact_id, count in id_counts.items()
            if count > 1
        ),
        key=lambda artifact_id: "" if artifact_id is None else str(artifact_id),
    )
    invalid_checksums = []
    for artifact in artifacts:
        for algorithm, digest in artifact.get("checksums", {}).items():
            if not validate_checksum(algorithm, digest):
                invalid_checksums.append({
                    "filename": artifact.get("filename"),
                    "algorithm": algorithm,
                })
    invalid_paths = []
    for artifact in artifacts:
        filename = artifact.get("filename")
        try:
            expected_path = encoded_mirror_path(filename)
        except (TypeError, ValueError):
            invalid_paths.append(filename)
            continue
        if artifact.get("mirror", {}).get("path") != expected_path:
            invalid_paths.append(filename)
    force_redirect_parameter = manifest.get("mirror", {}).get(
        "force_redirect_parameter"
    )
    force_redirect_valid = force_redirect_parameter == "force_redirect=true"
    report = {
        "compatible": not (
            missing_patterns
            or duplicate_ids
            or invalid_checksums
            or invalid_paths
            or not force_redirect_valid
        ),
        "missing_required_filenames": missing_patterns,
        "duplicate_artifact_ids": duplicate_ids,
        "invalid_checksums": invalid_checksums,
        "invalid_download_paths": invalid_paths,
        "force_redirect_parameter": force_redirect_parameter,
        "force_redirect_valid": force_redirect_valid,
    }
    return report
