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


def _fsync_directory(path: Path) -> None:
    """Make a completed directory rename durable where the platform supports it."""
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if directory_flag is None:
        return
    descriptor = os.open(path, os.O_RDONLY | directory_flag)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class ManifestPublisher:
    """Publish a validated candidate without damaging the last-known-good copy."""

    def __init__(self, output_dir: Path, keep_history: int = 20, sidecar: bool = True):
        self.output_dir = output_dir
        self.keep_history = max(0, keep_history)
        self.sidecar = sidecar

    @property
    def pointer_path(self) -> Path:
        return self.output_dir / "current.json"

    @property
    def revisions_dir(self) -> Path:
        return self.output_dir / "revisions"

    def _current_paths(self) -> tuple[Path, Path]:
        """Resolve both public files from one atomic pointer snapshot."""
        try:
            pointer = json.loads(self.pointer_path.read_text(encoding="utf-8"))
            revision = pointer["revision"]
            if (
                not isinstance(revision, str)
                or not revision
                or any(character not in "0123456789abcdef-" for character in revision)
            ):
                raise ValueError("invalid manifest revision pointer")
            revision_dir = ensure_within_root(
                self.revisions_dir / revision,
                self.output_dir,
            )
            manifest_path = ensure_within_root(
                revision_dir / "artifacts.json",
                self.output_dir,
            )
            sidecar_path = ensure_within_root(
                revision_dir / "artifacts.json.sha256",
                self.output_dir,
            )
            return manifest_path, sidecar_path
        except (
            FileNotFoundError,
            json.JSONDecodeError,
            KeyError,
            OSError,
            ValueError,
        ):
            return (
                self.output_dir / "artifacts.json",
                self.output_dir / "artifacts.json.sha256",
            )

    @property
    def manifest_path(self) -> Path:
        return self._current_paths()[0]

    @property
    def sidecar_path(self) -> Path:
        return self._current_paths()[1]

    def read_current(self) -> dict | None:
        manifest_path, _ = self._current_paths()
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def publish(self, candidate: ArtifactManifest | dict) -> dict:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.revisions_dir.mkdir(parents=True, exist_ok=True)
        ensure_within_root(self.pointer_path, self.output_dir)
        document = (
            candidate.model_dump(by_alias=True)
            if isinstance(candidate, ArtifactManifest)
            else deepcopy(candidate)
        )
        current_manifest_path, current_sidecar_path = self._current_paths()
        try:
            current = json.loads(current_manifest_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            current = None
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
                    current_sidecar_path.is_file()
                    and current_sidecar_path.read_bytes() == expected_sidecar
                )
            )
            if (
                current_manifest_path.read_bytes() == canonical_current
                and sidecar_is_current
            ):
                return {
                    "changed": False,
                    "path": str(current_manifest_path),
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
        revision_name = f"{digest}-{token[:8]}"
        revision_temp = self.revisions_dir / f".{revision_name}.tmp"
        revision_dir = self.revisions_dir / revision_name
        manifest_temp = revision_temp / "artifacts.json"
        sidecar_temp = revision_temp / "artifacts.json.sha256"
        pointer_temp = self.output_dir / f".current.json.{token}.tmp"
        ensure_within_root(revision_temp, self.output_dir)
        ensure_within_root(revision_dir, self.output_dir)
        ensure_within_root(pointer_temp, self.output_dir)
        pointer_switched = False
        try:
            revision_temp.mkdir()
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
            os.replace(revision_temp, revision_dir)
            _fsync_directory(self.revisions_dir)
            _write_fsynced(
                pointer_temp,
                (
                    json.dumps({"revision": revision_name}, sort_keys=True)
                    + "\n"
                ).encode("utf-8"),
            )
            os.replace(pointer_temp, self.pointer_path)
            pointer_switched = True
            _fsync_directory(self.output_dir)
            try:
                self._save_history(content, document["generated_at"])
            except Exception:
                logger.exception("Unable to retain manifest history snapshot")
            try:
                self._prune_revisions()
            except Exception:
                logger.exception("Unable to prune old manifest revision pairs")
            return {
                "changed": True,
                "path": str(revision_dir / "artifacts.json"),
                "revision": document["manifest_revision"],
                "generated_at": document["generated_at"],
                "sha256": digest,
            }
        finally:
            for temporary in (manifest_temp, sidecar_temp, pointer_temp):
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
            try:
                revision_temp.rmdir()
            except FileNotFoundError:
                pass
            if not pointer_switched:
                for path in (revision_dir / "artifacts.json.sha256", revision_dir / "artifacts.json"):
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                try:
                    revision_dir.rmdir()
                except FileNotFoundError:
                    pass

    def _prune_revisions(self) -> None:
        """Retain a bounded number of complete immutable revision pairs."""
        try:
            current_revision = json.loads(
                self.pointer_path.read_text(encoding="utf-8")
            )["revision"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError):
            return
        revision_dirs = sorted(
            (
                path
                for path in self.revisions_dir.iterdir()
                if path.is_dir() and not path.name.startswith(".")
            ),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        keep = {
            path.name
            for path in revision_dirs[:max(1, self.keep_history)]
        }
        keep.add(current_revision)
        for revision_dir in revision_dirs:
            if revision_dir.name in keep:
                continue
            ensure_within_root(revision_dir, self.output_dir)
            for filename in ("artifacts.json.sha256", "artifacts.json"):
                try:
                    (revision_dir / filename).unlink()
                except FileNotFoundError:
                    pass
            try:
                revision_dir.rmdir()
            except OSError:
                logger.warning(
                    "Unable to remove old manifest revision: %s",
                    revision_dir.name,
                )

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
