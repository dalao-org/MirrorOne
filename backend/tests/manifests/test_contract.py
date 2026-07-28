import json
from pathlib import Path

from app.manifests.contract import validate_lnmp_contract


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "lnmp-requirements.json"


def test_contract_reports_every_missing_pattern():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    report = validate_lnmp_contract({
        "mirror": {"force_redirect_parameter": "force_redirect=true"},
        "artifacts": [],
    }, fixture)
    assert report["compatible"] is False
    assert report["missing_required_filenames"] == fixture["required_filenames"]
    assert report["force_redirect_valid"] is True


def test_contract_accepts_exact_download_protocol():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    filenames = [
        "nginx-1.28.0.tar.gz",
        "php-8.4.12.tar.gz",
        "mysql-8.4.6-linux-glibc2.28-x86_64.tar.xz",
    ]
    artifacts = [
        {
            "id": f"item-{index}",
            "filename": filename,
            "aliases": [],
            "mirror": {"path": f"/src/{filename}"},
            "checksums": {},
        }
        for index, filename in enumerate(filenames)
    ]
    report = validate_lnmp_contract({
        "mirror": {"force_redirect_parameter": "force_redirect=true"},
        "artifacts": artifacts,
    }, fixture)
    assert report["compatible"] is True
    assert report["force_redirect_valid"] is True
