import json

import pytest

from app import redis_client


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.hashes = {}
        self.lists = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, **kwargs):
        if kwargs.get("nx") and key in self.values:
            return None
        self.values[key] = str(value)
        return True

    async def delete(self, key):
        self.values.pop(key, None)

    async def eval(self, script, key_count, key, token):
        if self.values.get(key) == token:
            await self.delete(key)
            return 1
        return 0

    async def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    async def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def hdel(self, key, *fields):
        for field in fields:
            self.hashes.get(key, {}).pop(field, None)

    async def lpush(self, key, value):
        self.lists.setdefault(key, []).insert(0, value)

    async def ltrim(self, key, start, end):
        self.lists[key] = self.lists.get(key, [])[start:end + 1]

    async def lrange(self, key, start, end):
        return self.lists.get(key, [])[start:end + 1]

    def pipeline(self, transaction=True):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def get(self, key):
        self.commands.append(("get", key))
        return self

    def hgetall(self, key):
        self.commands.append(("hgetall", key))
        return self

    async def execute(self):
        results = []
        for command, key in self.commands:
            if command == "get":
                results.append(await self.redis.get(key))
            else:
                results.append(await self.redis.hgetall(key))
        return results

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_v1_to_v2_migration_is_idempotent(monkeypatch):
    fake = FakeRedis()
    fake.hashes[redis_client.REDIRECT_RULES_KEY] = {
        "nginx-1.28.0.tar.gz": json.dumps({
            "url": "https://nginx.org/download/nginx-1.28.0.tar.gz",
            "version": "1.28.0",
            "source": "nginx",
            "updated_at": "2026-07-28T08:00:00Z",
        })
    }

    async def get_fake():
        return fake

    monkeypatch.setattr(redis_client, "get_redis", get_fake)
    assert await redis_client.migrate_redis_schema() == 2
    assert await redis_client.migrate_redis_schema() == 2
    migrated = json.loads(
        fake.hashes[redis_client.REDIRECT_RULES_KEY]["nginx-1.28.0.tar.gz"]
    )
    assert migrated["checksums"] == {}
    assert migrated["kind"] == "source"
    assert migrated["platform"]["arch"] == "any"


@pytest.mark.asyncio
async def test_filename_conflict_does_not_overwrite_valid_rule(monkeypatch):
    fake = FakeRedis()

    async def get_fake():
        return fake

    monkeypatch.setattr(redis_client, "get_redis", get_fake)
    common = {
        "filename": "same-1.0.0.tar.gz",
        "version": "1.0.0",
        "kind": "source",
    }
    assert await redis_client.set_redirect_rule(
        **common,
        url="https://one.example/same-1.0.0.tar.gz",
        source="one",
    )
    assert not await redis_client.set_redirect_rule(
        **common,
        url="https://two.example/same-1.0.0.tar.gz",
        source="two",
    )
    current = await redis_client.get_redirect_url(common["filename"])
    assert current["url"].startswith("https://one.example/")
    conflicts = await redis_client.get_redirect_conflicts()
    assert conflicts[0]["reason"] == "same_filename_different_source_url"


@pytest.mark.asyncio
async def test_checksum_change_is_recorded_without_silent_overwrite(monkeypatch):
    fake = FakeRedis()

    async def get_fake():
        return fake

    monkeypatch.setattr(redis_client, "get_redis", get_fake)
    values = {
        "filename": "php-8.4.12.tar.gz",
        "url": "https://php.net/distributions/php-8.4.12.tar.gz",
        "version": "8.4.12",
        "source": "php",
        "checksum_type": "sha256",
    }
    await redis_client.set_redirect_rule(**values, checksum="a" * 64)
    await redis_client.set_redirect_rule(**values, checksum="b" * 64)
    current = await redis_client.get_redirect_url(values["filename"])
    assert current["checksums"] == {"sha256": "a" * 64}
    assert current["pending_checksums"] == {"sha256": "b" * 64}
    events = await redis_client.get_manifest_events()
    assert events[0]["event"] == "upstream_checksum_changed"


@pytest.mark.asyncio
async def test_alias_resolves_to_canonical_rule(monkeypatch):
    fake = FakeRedis()

    async def get_fake():
        return fake

    monkeypatch.setattr(redis_client, "get_redis", get_fake)
    await redis_client.set_redirect_rule(
        filename="canonical-1.0.0.tar.gz",
        url="https://example.com/canonical-1.0.0.tar.gz",
        version="1.0.0",
        source="sample",
        aliases=["legacy-name.tar.gz"],
    )
    rule = await redis_client.get_redirect_url("legacy-name.tar.gz")
    assert rule["url"] == "https://example.com/canonical-1.0.0.tar.gz"
    assert rule["_canonical_filename"] == "canonical-1.0.0.tar.gz"


@pytest.mark.asyncio
async def test_identical_rule_preserves_discovery_timestamp(monkeypatch):
    fake = FakeRedis()

    async def get_fake():
        return fake

    monkeypatch.setattr(redis_client, "get_redis", get_fake)
    values = {
        "filename": "nginx-1.28.0.tar.gz",
        "url": "https://nginx.org/download/nginx-1.28.0.tar.gz",
        "version": "1.28.0",
        "source": "nginx",
    }
    await redis_client.set_redirect_rule(**values)
    first = await redis_client.get_redirect_url(values["filename"])
    await redis_client.set_redirect_rule(**values)
    second = await redis_client.get_redirect_url(values["filename"])
    assert second["updated_at"] == first["updated_at"]


@pytest.mark.asyncio
async def test_same_url_merges_optional_metadata_without_losing_checksum(monkeypatch):
    fake = FakeRedis()

    async def get_fake():
        return fake

    monkeypatch.setattr(redis_client, "get_redis", get_fake)
    common = {
        "filename": "mysql-8.4.6-linux-x86_64.tar.xz",
        "url": "https://example.com/mysql-8.4.6-linux-x86_64.tar.xz",
        "version": "8.4.6",
        "source": "mysql",
    }
    await redis_client.set_redirect_rule(
        **common,
        checksum="a" * 32,
        checksum_type="md5",
        kind="binary",
        platform={"os": "linux", "arch": "x86_64", "libc": None},
        channel="stable",
        aliases=["mysql-current.tar.xz"],
    )
    await redis_client.set_redirect_rule(**common)
    merged = await redis_client.get_redirect_url(common["filename"])
    assert merged["checksums"] == {"md5": "a" * 32}
    assert merged["kind"] == "binary"
    assert merged["platform"]["arch"] == "x86_64"
    assert merged["channel"] == "stable"
    assert merged["aliases"] == ["mysql-current.tar.xz"]


@pytest.mark.asyncio
async def test_manifest_snapshot_is_transactional_and_rejects_active_batch(monkeypatch):
    fake = FakeRedis()

    async def get_fake():
        return fake

    monkeypatch.setattr(redis_client, "get_redis", get_fake)
    await redis_client.set_redirect_rule(
        filename="nginx-1.28.0.tar.gz",
        url="https://nginx.org/download/nginx-1.28.0.tar.gz",
        version="1.28.0",
        source="nginx",
    )
    rules, versions, conflicts = await redis_client.get_manifest_snapshot()
    assert "nginx-1.28.0.tar.gz" in rules
    assert versions == {}
    assert conflicts == []
    token = await redis_client.begin_manifest_metadata_update()
    with pytest.raises(RuntimeError, match="in progress"):
        await redis_client.get_manifest_snapshot()
    with pytest.raises(RuntimeError, match="already in progress"):
        await redis_client.begin_manifest_metadata_update()
    await redis_client.end_manifest_metadata_update(token)


@pytest.mark.asyncio
async def test_canonical_filename_cannot_silently_take_over_an_alias(monkeypatch):
    fake = FakeRedis()

    async def get_fake():
        return fake

    monkeypatch.setattr(redis_client, "get_redis", get_fake)
    await redis_client.set_redirect_rule(
        filename="canonical.tar.gz",
        url="https://example.com/canonical.tar.gz",
        version="1",
        source="one",
        aliases=["legacy.tar.gz"],
    )
    assert not await redis_client.set_redirect_rule(
        filename="legacy.tar.gz",
        url="https://example.com/other.tar.gz",
        version="2",
        source="two",
    )
    conflict = (await redis_client.get_redirect_conflicts())[0]
    assert conflict["reason"] == "alias_conflict"
