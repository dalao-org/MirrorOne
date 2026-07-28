# MirrorOne Artifact Manifest v1

MirrorOne publishes a stable machine interface for LNMP, OneinStack, and other
installers:

```text
/manifests/artifacts.json
/manifests/artifacts.json.sha256
/manifests/schema/artifacts-v1.schema.json
```

The legacy download and metadata interfaces remain available:

```text
/src/{filename}
/oneinstack/src/{filename}
/resource.json
/suggest_versions.txt
/latest_meta.json
```

`force_redirect=true` continues to bypass local cache only for artifact download
paths. It has no effect on manifest responses.

## Integrity semantics

- `checksums` contains only digests published by the upstream provider.
- An empty `checksums` object is valid and never prevents publication or caching.
- SHA-256, SHA-384, and SHA-512 are marked strong. SHA-1 and MD5 are retained as
  legacy integrity metadata.
- MirrorOne computes a private observed SHA-256 for cached files. This is used to
  detect local corruption and is not presented as an upstream trust assertion.
- When an upstream checksum is available, the downloaded `.part` file must match
  before it can replace the final cache file.
- A mismatch is moved under `CACHE_PATH/quarantine/{source}/`; it is not served as
  cached and cannot overwrite a previous valid cache file.
- When no upstream checksum exists, the file is cached with
  `integrity_status=unverified_upstream_checksum_unavailable`.

The `.sha256` sidecar detects transfer or storage corruption. Because it is
served by the same host as the manifest, it is not an independent trust root.

## Snapshot and HTTP behavior

The builder reads one Redis snapshot, applies stable sorting, and validates all
artifacts and conflicts. The publisher writes and fsyncs an immutable revision
directory containing both `artifacts.json` and its checksum sidecar, then
atomically replaces `current.json`. Readers therefore see either the complete
previous pair or the complete new pair. A failed build or pointer replacement
keeps the last-known-good public pair.

Successful responses include:

```http
Content-Type: application/json; charset=utf-8
Cache-Control: public, max-age=300, stale-if-error=86400
ETag: "<content sha256>"
Last-Modified: ...
X-MirrorOne-Schema-Version: 1
X-MirrorOne-Manifest-Revision: ...
```

Clients should retain the last accepted revision and use conditional requests:

```bash
curl -fsS -D headers.txt \
  https://mirror.example.com/manifests/artifacts.json \
  -o artifacts.json

curl -i \
  -H 'If-None-Match: "<previous etag>"' \
  https://mirror.example.com/manifests/artifacts.json
```

An unchanged response returns `304 Not Modified`.

## Conflict behavior

`filename` remains the download protocol key. A filename discovered with two
different upstream URLs is recorded in `conflicts` and omitted from the new
artifact snapshot. The previously valid redirect rule is not silently
overwritten. Compatible old names are represented by `aliases`.

If an upstream changes a checksum for the same filename and URL, MirrorOne keeps
the previous published checksum, records an `upstream_checksum_changed` event,
and exposes the condition for operator review.

## Upgrade and migration

1. Back up the SQLite data, Redis volume, and cache directory.
2. Set `MANIFEST_PUBLIC_BASE_URL`, `MANIFEST_GENERATOR_COMMIT`, and
   `MANIFEST_INSTANCE_ID` for the deployment.
3. Rebuild and restart the backend and frontend containers.
4. Request `/health`. The `manifest.state` field should be `healthy`.
5. Request `artifacts.json`, its sidecar, and the Schema.
6. Run an existing LNMP/OneinStack download once with and without
   `force_redirect=true`.

On startup, Redis schema v1 is migrated idempotently to v2 by adding defaults
only. The migration does not delete rules, clear Redis, or re-run scrapers.
Deployments can roll back the application version without clearing Redis;
v1 readers ignore the additional JSON fields.

`suggest_versions.txt` is generated from the last successful Manifest snapshot.
`resource.json` retains its original response shape.

## Administration and monitoring

Authenticated endpoints:

```text
POST /api/manifests/rebuild
GET  /api/manifests/status
```

The Dashboard shows revision, last success, artifact count, checksum coverage,
cache coverage, conflicts, and the most recent error. `/health` changes to
`degraded` when a Manifest build fails while continuing to serve the
last-known-good snapshot.

Prometheus text metrics are available at `/metrics`:

```text
mirrorone_manifest_last_success_timestamp
mirrorone_manifest_build_duration_seconds
mirrorone_manifest_artifact_count
mirrorone_manifest_checksum_available_count
mirrorone_manifest_checksum_missing_count
mirrorone_manifest_conflict_count
mirrorone_cache_checksum_mismatch_total
mirrorone_cache_unverified_artifact_count
```

Private history is stored under
`MANIFEST_OUTPUT_DIR/history/` and trimmed to `MANIFEST_KEEP_HISTORY`.

## Troubleshooting

### Manifest returns 503

No valid snapshot has been published. Check `/api/manifests/status`, Redis
connectivity, output-directory permissions, disk space, unsafe filenames or
URLs, unresolved recommendation versions, and filename conflicts. Fix the
source condition and run the authenticated rebuild endpoint.

### Health is degraded but downloads still work

The latest build failed and MirrorOne is serving a last-known-good Manifest.
This is deliberate. Inspect `last_error` and `recent_events` in the status API.

### A cache file is in quarantine

Do not rename it into the live cache. Compare the recorded expected and actual
digest, verify the upstream release page, and check whether the upstream
replaced a same-named file. Re-run the scraper only after the discrepancy is
understood.

### Version suggestions differ after upgrade

The text interface now follows the last successful snapshot. If a new Redis
version recommendation does not resolve to an artifact, publication fails and
the previous snapshot remains active; this prevents a recommendation from
pointing at a missing download.

## Tests

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp
```

The suite covers algorithm normalization and lengths, empty/MD5/SHA-256
checksum samples, source/binary/patch/alias/cache/legacy Schema cases, stable
sorting, old Redis compatibility, conflicts, checksum changes, quarantine,
atomic last-known-good rollback, conditional HTTP requests, and the LNMP
filename contract fixture.
