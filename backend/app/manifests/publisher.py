"""Atomic publication and history retention for artifact manifests."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from copy import deepcopy
from pathlib import Path

from .models import ArtifactManifest
from .validator import (
    ensure_within_root,
    validate_manifest_dict,
    validate_manifest_schema,
)


logger = logging.getLogger(__name__)


def _json_bytes(document: dict) -> bytes:
    return (
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _semantic_document(document: dict) -> dict:
    value = deepcopy(document)
    value.pop("generated_at", None)
    value.pop("manifest_revision", None)
    return value


def _write_fsynced(path: Path, content: bytes) -> None:
    with path.open("wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


class ManifestPublisher:
    """Publish a validated candidate without damaging the last-known-good copy."""

    def __init__(self, output_dir: Path, keep_history: int = 20, sidecar: bool = True):
        self.output_dir = output_dir
        self.keep_history = max(0, keep_history)
        self.sidecar = sidecar

    @property
    def manifest_path(self) -> Path:
        return self.output_dir / "artifacts.json"

    @property
    def sidecar_path(self) -> Path:
        return self.output_dir / "artifacts.json.sha256"

    def read_current(self) -> dict | None:
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def publish(self, candidate: ArtifactManifest | dict) -> dict:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ensure_within_root(self.manifest_path, self.output_dir)
        document = (
            candidate.model_dump(by_alias=True)
            if isinstance(candidate, ArtifactManifest)
            else deepcopy(candidate)
        )
        current = self.read_current()
        if current and _semantic_document(current) == _semantic_document(document):
            ArtifactManifest.model_validate(current)
            validate_manifest_dict(current)
            validate_manifest_schema(current)
            canonical_current = _json_bytes(current)
            current_digest = hashlib.sha256(canonical_current).hexdigest()
            expected_sidecar = f"{current_digest}  artifacts.json\n".encode("ascii")
            sidecar_is_current = (
                not self.sidecar
                or (
                    self.sidecar_path.is_file()
                    and self.sidecar_path.read_bytes() == expected_sidecar
                )
            )
            if (
                self.manifest_path.read_bytes() == canonical_current
                and sidecar_is_current
            ):
                return {
                    "changed": False,
                    "path": str(self.manifest_path),
                    "revision": current["manifest_revision"],
                    "generated_at": current["generated_at"],
                    "sha256": current_digest,
                }
            document = current

        ArtifactManifest.model_validate(document)
        validate_manifest_dict(document)
        validate_manifest_schema(document)
        content = _json_bytes(document)
        digest = hashlib.sha256(content).hexdigest()
        token = uuid.uuid4().hex
        manifest_temp = self.output_dir / f".artifacts.json.{token}.tmp"
        sidecar_temp = self.output_dir / f".artifacts.json.sha256.{token}.tmp"
        ensure_within_root(manifest_temp, self.output_dir)
        previous_manifest = self.manifest_path.read_bytes() if self.manifest_path.exists() else None
        previous_sidecar = self.sidecar_path.read_bytes() if self.sidecar_path.exists() else None
        try:
            _write_fsynced(manifest_temp, content)
            parsed = json.loads(manifest_temp.read_text(encoding="utf-8"))
            ArtifactManifest.model_validate(parsed)
            validate_manifest_dict(parsed)
            validate_manifest_schema(parsed)
            if self.sidecar:
                _write_fsynced(
                    sidecar_temp,
                    f"{digest}  artifacts.json\n".encode("ascii"),
                )
            try:
                os.replace(manifest_temp, self.manifest_path)
                if self.sidecar:
                    os.replace(sidecar_temp, self.sidecar_path)
            except Exception:
                self._restore_previous(previous_manifest, previous_sidecar)
                raise
            try:
                self._save_history(content, document["generated_at"])
            except Exception:
                logger.exception("Unable to retain manifest history snapshot")
            return {
                "changed": True,
                "path": str(self.manifest_path),
                "revision": document["manifest_revision"],
                "generated_at": document["generated_at"],
                "sha256": digest,
            }
        finally:
            for temporary in (manifest_temp, sidecar_temp):
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass

    def _restore_previous(
        self,
        previous_manifest: bytes | None,
        previous_sidecar: bytes | None,
    ) -> None:
        """Best-effort rollback when one file of the public pair cannot be replaced."""
        for path, previous in (
            (self.manifest_path, previous_manifest),
            (self.sidecar_path, previous_sidecar),
        ):
            if previous is None:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                continue
            temporary = self.output_dir / f".{path.name}.rollback.{uuid.uuid4().hex}"
            _write_fsynced(temporary, previous)
            os.replace(temporary, path)

    def _save_history(self, content: bytes, generated_at: str) -> None:
        if self.keep_history <= 0:
            return
        history_dir = self.output_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        stamp = (
            generated_at.replace("-", "").replace(":", "").replace("Z", "Z")
        )
        history_path = history_dir / f"artifacts-{stamp}.json"
        ensure_within_root(history_path, self.output_dir)
        if not history_path.exists():
            temporary = history_dir / f".{history_path.name}.{uuid.uuid4().hex}.tmp"
            _write_fsynced(temporary, content)
            os.replace(temporary, history_path)
        history = sorted(history_dir.glob("artifacts-*.json"), reverse=True)
        for old_path in history[self.keep_history:]:
            ensure_within_root(old_path, self.output_dir).unlink()
