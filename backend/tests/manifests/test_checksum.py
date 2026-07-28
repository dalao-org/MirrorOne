from pathlib import Path

import pytest

from app.manifests.checksum import (
    choose_strongest,
    digest_file,
    normalize_algorithm,
    validate_checksum,
)
from app.scrapers.base import Resource, normalize_resource
from app.manifests.validator import validate_filename, validate_source_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SHA-512", "sha512"),
        ("sha_384", "sha384"),
        ("SHA256SUM", "sha256"),
        ("sha-1", "sha1"),
        ("MD5SUM", "md5"),
        ("crc32", None),
    ],
)
def test_algorithm_normalization(raw, expected):
    assert normalize_algorithm(raw) == expected


@pytest.mark.parametrize(
    ("algorithm", "length"),
    [("md5", 32), ("sha1", 40), ("sha256", 64), ("sha384", 96), ("sha512", 128)],
)
def test_checksum_lengths(algorithm, length):
    assert validate_checksum(algorithm, "a" * length)
    assert not validate_checksum(algorithm, "a" * (length - 1))
    assert not validate_checksum(algorithm, "z" * length)


def test_resource_normalization_keeps_artifact_when_checksum_is_invalid():
    resource, warnings = normalize_resource(Resource(
        file_name="nginx-1.28.0.tar.gz",
        url="https://nginx.org/download/nginx-1.28.0.tar.gz",
        version=" 1.28.0 ",
        checksum="bad",
        checksum_type="SHA-256",
    ))
    assert resource.version == "1.28.0"
    assert resource.checksums == {}
    assert resource.checksum_unavailable_reason == "invalid_upstream_checksum_format"
    assert warnings


def test_choose_strongest_and_digest(tmp_path: Path):
    path = tmp_path / "payload"
    path.write_bytes(b"mirrorone")
    sha256 = digest_file(path, "sha256")
    selected = choose_strongest({"md5": "a" * 32, "sha256": sha256})
    assert selected == ("sha256", sha256)


def test_filename_and_source_url_security_policy():
    assert validate_source_url(
        "http://www.memcached.org/files/memcached-1.6.0.tar.gz"
    ).startswith("http://")
    with pytest.raises(ValueError):
        validate_source_url("http://example.com/file.tar.gz")
    with pytest.raises(ValueError):
        validate_source_url("https://127.0.0.1/file.tar.gz")
    with pytest.raises(ValueError):
        validate_source_url("file:///tmp/file.tar.gz")
    with pytest.raises(ValueError):
        validate_filename("../escape.tar.gz")
