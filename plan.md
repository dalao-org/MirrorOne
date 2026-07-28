# MirrorOne `manifests/artifacts.json` 制品清单设计与实施计划

## 1. 文档目的

本文档用于指导 MirrorOne 增加标准化制品清单：

```text
/manifests/artifacts.json
```

该清单将作为 MirrorOne 与 LNMP、OneinStack 及其他安装程序之间的稳定机器接口，用于描述：

- MirrorOne 当前可以解析和提供的制品；
- 制品的精确文件名、版本、类型和平台要求；
- 制品对应的原始上游地址；
- MirrorOne 下载路径；
- 上游是否提供 checksum；
- checksum 的算法、内容和来源；
- 制品当前是否已缓存；
- 建议版本与兼容版本；
- 生成时间、数据来源和协议版本。

本设计不改变 MirrorOne 当前核心功能：

- 保留 `/src/{filename}`；
- 保留 `/oneinstack/src/{filename}`；
- 保留 `redirect` 与 `cache` 两种模式；
- 保留 `force_redirect=true`；
- 保留 `suggest_versions.txt`；
- 保留 `resource.json`；
- 不要求所有上游必须提供 checksum；
- 不因为缺少 checksum 而停止收录或缓存上游制品。

MirrorOne 当前已经明确将 LNMP 和 OneinStack 列为兼容脚本，并提供重定向与本地缓存两种工作模式。

------

## 2. 当前实现基础

### 2.1 已有的下载路径

MirrorOne 当前提供：

```text
GET /src/{filename}
GET /oneinstack/src/{filename}
```

其中：

- 默认 `redirect` 模式返回原始上游地址；
- `cache` 模式在缓存命中时直接返回本地文件；
- 缓存未命中时回退到原始上游；
- 请求带有 `force_redirect=true` 时，强制返回原始上游地址。

因此，新清单不需要设计新的下载协议，只需要把现有协议正式结构化。

### 2.2 已有的 checksum 数据结构

MirrorOne 的 Scraper 数据结构已经包含：

```python
checksum: str | None
checksum_type: str | None
```

部分 Scraper 已经会从上游页面读取 checksum。例如 PHP Scraper 会读取 PHP 官方页面发布的 SHA-256。

因此，`artifacts.json` 不需要重新发明 checksum 抓取机制，而是需要把已有信息贯通到：

```text
Scraper
  → ScrapeResult
  → Redis
  → Cache
  → artifacts.json
  → LNMP
```

### 2.3 当前信息丢失点

当前 Scheduler 将 Scraper 结果写入 Redis 时，仅传递：

```text
filename
url
version
source
```

并没有传递 `checksum` 和 `checksum_type`。

Redis 中的规则也只保存：

```json
{
  "url": "...",
  "version": "...",
  "source": "...",
  "updated_at": "..."
}
```

这意味着 checksum 虽然在 Scraper 层被发现，但在发布层之前已经丢失。

`resource.json` 当前也只输出文件名、URL 和版本，没有输出 checksum。

第一阶段实施重点就是修复这条元数据链路。

------

# 3. 核心设计原则

## 3.1 checksum 是可选能力，不是制品存在的前提

上游可能出现以下情况：

1. 提供 SHA-512；
2. 提供 SHA-256；
3. 只提供 SHA-1；
4. 只提供 MD5；
5. 只提供 GPG 签名；
6. 完全不提供 checksum；
7. 提供 checksum 文件，但格式无法可靠解析；
8. 历史归档页面中的 checksum 已失效或消失。

MirrorOne 必须兼容全部情况。

规则定义如下：

| 上游状态                  | MirrorOne 行为               |
| ------------------------- | ---------------------------- |
| 有官方 checksum           | 收录并标记为 `upstream`      |
| 有多个官方 checksum       | 全部收录                     |
| 只有 MD5/SHA-1            | 收录，但标记为弱算法         |
| 没有 checksum             | 正常收录，`checksums` 为空   |
| checksum 格式解析失败     | 正常收录，记录解析警告       |
| checksum 与下载文件不一致 | 不把该缓存文件提升为有效缓存 |
| 上游 checksum 后续变化    | 生成异常事件，不静默覆盖     |

缺少 checksum 不等于文件无效，也不等于 MirrorOne 应该拒绝提供该文件。

## 3.2 上游 checksum 与 MirrorOne 自计算摘要必须分开

为了避免把“镜像自己计算的摘要”误解为“上游发布的可信摘要”，需要区分：

```json
"checksums": {
  "sha256": "上游发布的摘要"
}
```

与：

```json
"observed_digests": {
  "sha256": "MirrorOne 下载后自行计算的摘要"
}
```

语义如下：

- `checksums`：来自上游发布信息；
- `observed_digests`：MirrorOne 对实际缓存内容的观测结果；
- `observed_digests` 不能冒充上游 checksum；
- LNMP 默认只把 `checksums` 视为上游完整性验证依据；
- `observed_digests` 可用于镜像节点间一致性检查和缓存损坏检查。

第一版可以暂不公开 `observed_digests`，但数据结构应预留。

## 3.3 清单是快照，而不是动态拼装结果

一次请求 `artifacts.json` 时，不应临时遍历 Redis 并边读边生成。否则可能出现：

- Scraper 正在更新；
- 部分旧规则已删除；
- 部分新规则尚未写入；
- `suggest_versions.txt` 与制品列表不一致；
- 同一个响应中混入不同抓取批次的数据。

正确模型是：

```text
Scraper 批次完成
    ↓
构建候选快照
    ↓
Schema 校验
    ↓
冲突检查
    ↓
原子写入 artifacts.json.tmp
    ↓
fsync
    ↓
rename 为 artifacts.json
```

任何生成失败都必须保留上一份有效快照。

## 3.4 文件名兼容必须保持

LNMP 当前大量下载逻辑依赖精确文件名：

```text
nginx-1.x.x.tar.gz
php-8.x.x.tar.gz
mysql-x.x.x-linux-glibc2.28-x86_64.tar.xz
```

MirrorOne 当前也是使用 `filename` 查询 Redis，找不到时直接返回 404。

因此：

- `filename` 必须继续作为下载路径的核心键；
- Manifest 额外增加稳定的 `id`，但不能立即替代文件名路径；
- 不允许在生成清单时自动重命名上游文件；
- 对兼容别名必须通过 `aliases` 显式表达；
- 同名文件指向不同内容时必须触发冲突。

------

# 4. 清单协议

## 4.1 规范路径

Canonical URL：

```text
https://mirror.example.com/manifests/artifacts.json
```

配套文件：

```text
/manifests/artifacts.json
/manifests/artifacts.json.sha256
/manifests/schema/artifacts-v1.schema.json
```

第一版必须实现前两个；JSON Schema 文件建议在同一版本完成。

## 4.2 HTTP 行为

`artifacts.json` 建议返回：

```http
Content-Type: application/json; charset=utf-8
Cache-Control: public, max-age=300, stale-if-error=86400
ETag: "manifest-revision"
Last-Modified: ...
X-MirrorOne-Schema-Version: 1
X-MirrorOne-Manifest-Revision: ...
```

必须支持：

```http
If-None-Match
If-Modified-Since
```

未变化时返回：

```http
304 Not Modified
```

Manifest 不受 `force_redirect` 影响。`force_redirect` 只作用于制品下载路径。

------

# 5. `artifacts.json` 顶层结构

建议第一版结构如下：

```json
{
  "$schema": "/manifests/schema/artifacts-v1.schema.json",
  "schema_name": "mirrorone-artifacts",
  "schema_version": 1,
  "manifest_revision": "2026-07-28T08:15:30Z-4f9e8d2",
  "generated_at": "2026-07-28T08:15:30Z",

  "generator": {
    "name": "MirrorOne",
    "version": "1.1.0",
    "commit": "4f9e8d2",
    "instance_id": "mirror.dal.ao"
  },

  "mirror": {
    "base_url": "https://mirror.dal.ao",
    "download_path_template": "/src/{filename}",
    "legacy_path_template": "/oneinstack/src/{filename}",
    "force_redirect_parameter": "force_redirect=true",
    "supported_modes": [
      "redirect",
      "cache"
    ],
    "current_mode": "cache"
  },

  "checksum_policy": {
    "source": "upstream",
    "checksum_optional": true,
    "missing_checksum_allowed": true,
    "mirror_computed_digest_is_authoritative": false,
    "preferred_algorithms": [
      "sha512",
      "sha256",
      "sha1",
      "md5"
    ]
  },

  "version_recommendations": {
    "nginx_ver": "1.28.0",
    "php84_ver": "8.4.12",
    "php85_ver": "8.5.0",
    "mysql84_ver": "8.4.6"
  },

  "artifacts": [],

  "conflicts": [],

  "statistics": {
    "artifact_count": 0,
    "with_upstream_checksum": 0,
    "without_upstream_checksum": 0,
    "cached": 0,
    "not_cached": 0
  }
}
```

## 5.1 `manifest_revision`

推荐格式：

```text
<UTC 时间>-<生成代码 commit 短 SHA>
```

例如：

```text
2026-07-28T08:15:30Z-4f9e8d2
```

要求：

- 每次内容改变时必须变化；
- 相同内容重复生成时可以保持不变；
- 不应依赖数据库自增 ID；
- LNMP 可以把它写入安装锁定记录。

## 5.2 `version_recommendations`

MirrorOne 当前通过 `suggest_versions.txt` 提供版本建议。

新的 Manifest 应将同一份数据放入：

```json
"version_recommendations": {}
```

之后：

```text
suggest_versions.txt
```

应从 Manifest 快照反向生成，避免出现两套版本建议数据源。

------

# 6. 单个 Artifact 结构

## 6.1 有上游 checksum 的示例

```json
{
  "id": "php:8.4.12:source:any",
  "component": "php",
  "version": "8.4.12",
  "channel": "supported",
  "kind": "source",

  "filename": "php-8.4.12.tar.gz",
  "aliases": [],

  "platform": {
    "os": "any",
    "arch": "any",
    "libc": null
  },

  "source": {
    "provider": "php.net",
    "url": "https://www.php.net/distributions/php-8.4.12.tar.gz",
    "discovered_at": "2026-07-28T07:58:20Z"
  },

  "mirror": {
    "path": "/src/php-8.4.12.tar.gz",
    "legacy_path": "/oneinstack/src/php-8.4.12.tar.gz",
    "available": true,
    "cache_status": "cached",
    "cached_at": "2026-07-28T08:03:10Z"
  },

  "checksums": {
    "sha256": "..."
  },

  "checksum_metadata": {
    "available": true,
    "provenance": "upstream",
    "source_url": "https://www.php.net/downloads.php",
    "strength": "strong"
  },

  "size": {
    "bytes": 13245678,
    "source": "download"
  },

  "updated_at": "2026-07-28T08:03:10Z"
}
```

## 6.2 没有上游 checksum 的示例

```json
{
  "id": "nginx:1.28.0:source:any",
  "component": "nginx",
  "version": "1.28.0",
  "channel": "stable",
  "kind": "source",

  "filename": "nginx-1.28.0.tar.gz",
  "aliases": [],

  "platform": {
    "os": "any",
    "arch": "any",
    "libc": null
  },

  "source": {
    "provider": "nginx.org",
    "url": "https://nginx.org/download/nginx-1.28.0.tar.gz",
    "discovered_at": "2026-07-28T07:55:00Z"
  },

  "mirror": {
    "path": "/src/nginx-1.28.0.tar.gz",
    "legacy_path": "/oneinstack/src/nginx-1.28.0.tar.gz",
    "available": true,
    "cache_status": "not_cached",
    "cached_at": null
  },

  "checksums": {},

  "checksum_metadata": {
    "available": false,
    "provenance": "none",
    "source_url": null,
    "strength": "none",
    "reason": "upstream_not_published"
  },

  "size": {
    "bytes": null,
    "source": "unknown"
  },

  "updated_at": "2026-07-28T07:55:00Z"
}
```

重点是：

```json
"checksums": {}
```

属于合法状态，不是 Schema 错误。

## 6.3 只有 MD5 的示例

```json
{
  "checksums": {
    "md5": "..."
  },
  "checksum_metadata": {
    "available": true,
    "provenance": "upstream",
    "strength": "legacy"
  }
}
```

MirrorOne 不应删除上游提供的 MD5，但必须让消费者知道这是弱算法。

------

# 7. 字段规范

## 7.1 必填字段

每个 Artifact 必须具有：

```text
id
component
version
kind
filename
source.url
source.provider
mirror.path
mirror.available
mirror.cache_status
checksums
checksum_metadata
updated_at
```

## 7.2 `id` 规则

建议格式：

```text
<component>:<version>:<kind>:<platform>
```

例如：

```text
nginx:1.28.0:source:any
mysql:8.4.6:binary:linux-x86_64-glibc2.28
php-redis:6.2.0:source:any
```

`id` 用于程序精确选择制品，但下载路径继续使用 `filename`。

## 7.3 `kind`

允许值：

```text
source
binary
patch
extension
module
certificate
script
archive
jar
key
metadata
```

例如：

```text
mysql-8.4.6-linux-glibc2.28-x86_64.tar.xz → binary
fpm-race-condition.patch                  → patch
cacert.pem                                → certificate
catalina-jmx-remote.jar                   → jar
```

## 7.4 `platform`

源码包：

```json
{
  "os": "any",
  "arch": "any",
  "libc": null
}
```

二进制包：

```json
{
  "os": "linux",
  "arch": "x86_64",
  "libc": "glibc2.28"
}
```

未知平台不能根据文件名盲目推断，应使用：

```json
{
  "os": "unknown",
  "arch": "unknown",
  "libc": null
}
```

## 7.5 `channel`

建议值：

```text
recommended
stable
mainline
supported
legacy
eol
archive
unknown
```

这只是描述信息，不代表 MirrorOne 必须拒绝提供 EOL 制品。

------

# 8. Redis 数据模型调整

## 8.1 扩展重定向规则

当前：

```python
async def set_redirect_rule(
    filename: str,
    url: str,
    version: str,
    source: str,
)
```

应调整为接收完整结构：

```python
async def set_redirect_rule(
    *,
    filename: str,
    url: str,
    version: str,
    source: str,
    checksum: str | None = None,
    checksum_type: str | None = None,
    kind: str = "source",
    platform: dict | None = None,
    channel: str | None = None,
    aliases: list[str] | None = None,
) -> None:
    ...
```

Redis 中保存：

```json
{
  "url": "...",
  "version": "...",
  "source": "php",
  "checksum": "...",
  "checksum_type": "sha256",
  "kind": "source",
  "platform": {
    "os": "any",
    "arch": "any"
  },
  "channel": "supported",
  "aliases": [],
  "updated_at": "..."
}
```

## 8.2 兼容旧 Redis 数据

Manifest 生成器必须兼容旧规则缺少新字段：

```python
checksum = rule.get("checksum")
checksum_type = rule.get("checksum_type")
kind = rule.get("kind", "source")
platform = rule.get("platform") or default_platform()
```

不能要求部署者先清空 Redis。

## 8.3 Redis Schema 版本

新增：

```text
meta:redis_schema_version = 2
```

启动时执行幂等迁移：

```text
v1 → v2
```

迁移只补默认字段，不重新抓取、不删除旧规则。

------

# 9. Scraper 数据结构调整

当前 `Resource` 只包含基本字段。

建议扩展：

```python
@dataclass
class Resource:
    file_name: str
    url: str
    version: str

    checksum: str | None = None
    checksum_type: str | None = None

    kind: str = "source"
    channel: str | None = None
    aliases: list[str] = field(default_factory=list)

    os: str = "any"
    arch: str = "any"
    libc: str | None = None

    checksum_source_url: str | None = None
    checksum_unavailable_reason: str | None = None
```

每个 Scraper 不需要立即填写全部字段。

BaseScraper 应负责默认值和标准化：

```python
def normalize_resource(resource: Resource) -> Resource:
    resource.file_name = sanitize_filename(resource.file_name)
    resource.checksum_type = normalize_algorithm(resource.checksum_type)
    resource.version = resource.version.strip()
    return resource
```

------

# 10. checksum 标准化

## 10.1 支持算法

第一版支持：

```text
sha512
sha384
sha256
sha1
md5
```

统一转换成小写名称。

禁止出现：

```text
SHA-256
sha_256
SHA256SUM
```

这些输入都应标准化为：

```text
sha256
```

## 10.2 格式验证

摘要必须满足算法长度：

| 算法    | 十六进制字符长度 |
| ------- | ---------------- |
| MD5     | 32               |
| SHA-1   | 40               |
| SHA-256 | 64               |
| SHA-384 | 96               |
| SHA-512 | 128              |

格式不合法时：

- 不写入 `checksums`；
- 设置 `reason=invalid_upstream_checksum_format`；
- 记录 Scraper Warning；
- 不阻止资源本身发布。

## 10.3 多 checksum 支持

现有模型一次只能表示一种 checksum。Manifest 必须支持多个：

```json
"checksums": {
  "sha256": "...",
  "sha512": "..."
}
```

Scraper 数据结构后续应逐步迁移为：

```python
checksums: dict[str, str]
```

第一阶段可以兼容转换：

```python
if resource.checksum and resource.checksum_type:
    checksums[resource.checksum_type] = resource.checksum
```

------

# 11. Cache 模式完整性处理

MirrorOne 当前缓存流程采用临时文件下载，再重命名为正式文件。

应扩展为：

```text
下载到 .part
    ↓
检查 HTTP 状态
    ↓
检查实际文件大小 > 0
    ↓
上游 checksum 存在？
    ├─ 是：计算对应摘要并比较
    │       ├─ 一致：提升为正式缓存
    │       └─ 不一致：移入 quarantine，禁止发布为 cached
    └─ 否：正常提升为正式缓存，并标记 unverified
```

## 11.1 checksum 存在时

伪代码：

```python
if resource.checksums:
    algorithm = choose_strongest(resource.checksums)
    actual = digest(temp_path, algorithm)
    expected = resource.checksums[algorithm]

    if not constant_time_equal(actual, expected):
        quarantine(temp_path, reason="checksum_mismatch")
        raise CacheIntegrityError(...)
```

必须做到：

- 不覆盖已有有效缓存；
- 不把失败文件重命名到正式路径；
- 不把 `cache_status` 标记为 `cached`；
- 记录 expected 与 actual，但日志中不需要输出完整 URL 查询参数。

## 11.2 checksum 缺失时

允许正常缓存：

```text
cache_status = cached
integrity_status = unverified_upstream_checksum_unavailable
```

不能把它描述为：

```text
verified
```

建议 Manifest 表示：

```json
"mirror": {
  "cache_status": "cached",
  "integrity_status": "unverified_upstream_checksum_unavailable"
}
```

## 11.3 缓存文件定期巡检

对于 checksum 可用的制品：

```text
定期重新计算摘要
```

对于 checksum 不可用的制品：

```text
可以计算 observed digest 检测磁盘静默损坏
```

但 observed digest 只与 MirrorOne 自己上次观测值比较，不作为上游身份认证。

------

# 12. Manifest 生成模块

建议新增：

```text
backend/app/manifests/
├── __init__.py
├── builder.py
├── models.py
├── validator.py
├── publisher.py
├── checksum.py
└── schema/
    └── artifacts-v1.schema.json
```

## 12.1 Builder

职责：

- 从 Redis 读取完整资源快照；
- 读取版本建议；
- 读取 MirrorOne 配置；
- 读取缓存状态；
- 构建标准 Artifact；
- 生成统计数据；
- 检测冲突；
- 排序输出。

必须采用稳定排序：

```text
component
version
kind
platform.arch
filename
```

这样相同数据每次生成的 JSON 内容一致。

## 12.2 Validator

检查：

- Schema 是否符合；
- `filename` 是否为安全 basename；
- `source.url` 是否是合法 HTTP/HTTPS URL；
- `mirror.path` 是否与 filename 一致；
- checksum 长度是否合法；
- Artifact ID 是否唯一；
- filename 是否冲突；
- alias 是否冲突；
- version recommendation 是否能解析到 Artifact；
- cache 文件是否逃逸出 cache 根目录。

## 12.3 Publisher

输出路径：

```text
/app/data/manifests/current.json
/app/data/manifests/revisions/<revision>/artifacts.json
/app/data/manifests/revisions/<revision>/artifacts.json.sha256
```

原子发布流程：

```python
write_json(revision_dir / "artifacts.json")
write_sha256_sidecar(revision_dir / "artifacts.json.sha256")
flush_and_fsync_revision_pair()
validate(revision_dir / "artifacts.json")
os.replace(temp_revision_dir, immutable_revision_dir)
os.replace(temp_current_pointer, current_pointer)
```

Manifest 与 sidecar 先写入同一个不可变 revision 目录；只有两者都完整落盘并
通过验证后才原子切换 `current_pointer`。读取端必须先读取一次 pointer，再从
该 revision 目录读取两份文件，避免观察到新 Manifest 与旧 sidecar 的组合。

发布失败时：

- 不删除旧 Manifest；
- 暴露最近一次成功时间；
- Dashboard 显示失败；
- 健康检查进入 degraded，而不是直接杀死服务。

------

# 13. 文件名与别名冲突

## 13.1 同名同 URL

可以合并：

```text
filename 相同
source URL 相同
checksum 相同或其中一方为空
```

保留更新时间较新、信息更完整的条目。

## 13.2 同名不同 URL

视为冲突：

```text
filename 相同
source URL 不同
```

不能静默采用最后写入者。

处理方式：

```json
"conflicts": [
  {
    "filename": "example.tar.gz",
    "reason": "same_filename_different_source_url",
    "candidates": [...]
  }
]
```

同时：

- 不把冲突条目加入可下载 Artifact；
- 保留上一份有效重定向规则；
- Dashboard 显示人工处理要求。

## 13.3 aliases

例如某些脚本长期使用旧文件名，可以定义：

```json
"aliases": [
  "legacy-name.tar.gz"
]
```

MirrorOne 应为 alias 建立相同重定向规则，但 Manifest 必须明确：

```text
canonical filename
alias filename
```

------

# 14. API 与向后兼容

## 14.1 新增路由

建议新增：

```text
GET /manifests/artifacts.json
GET /manifests/artifacts.json.sha256
GET /manifests/schema/artifacts-v1.schema.json
```

可选管理接口：

```text
POST /api/manifests/rebuild
GET  /api/manifests/status
```

管理接口需要认证。

## 14.2 保留旧接口

以下接口不能删除：

```text
/src/{filename}
/oneinstack/src/{filename}
/resource.json
/suggest_versions.txt
/latest_meta.json
```

Manifest 上线后：

- `suggest_versions.txt` 从 Manifest 快照生成；
- `resource.json` 可以继续保持旧结构；
- 可增加 `resource-v2.json`，但不是本计划必需项。

## 14.3 Schema 版本兼容

消费者必须根据：

```json
"schema_version": 1
```

选择解析器。

未来新增字段不增加 major version；删除字段、修改字段语义或改变必填规则时，才升级为：

```text
schema_version = 2
```

------

# 15. 配置项

建议增加：

```text
MANIFEST_ENABLED=true
MANIFEST_OUTPUT_DIR=/app/data/manifests
MANIFEST_PUBLIC_BASE_URL=https://mirror.dal.ao
MANIFEST_REBUILD_AFTER_SCRAPE=true
MANIFEST_INCLUDE_CACHE_STATUS=true
MANIFEST_KEEP_HISTORY=20
MANIFEST_CHECKSUM_SIDECAR=true
```

后台 Settings 增加：

```text
manifest_enabled
manifest_public_base_url
manifest_keep_history
manifest_include_cache_status
```

默认启用。

------

# 16. Manifest 历史版本

建议保存最近若干快照：

```text
/app/data/manifests/history/
  artifacts-20260728T081530Z.json
  artifacts-20260728T141530Z.json
```

用途：

- 追查版本推荐变化；
- 追查 checksum 变化；
- 比较上游 URL 变化；
- LNMP 安装故障复现；
- 检测上游是否替换了同名文件。

历史文件不需要公开访问，默认保留最近 20 份。

------

# 17. 可观测性

新增指标：

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

新增结构化日志事件：

```text
manifest_build_started
manifest_build_succeeded
manifest_build_failed
manifest_conflict_detected
upstream_checksum_changed
cache_checksum_mismatch
cache_promoted_without_upstream_checksum
```

Dashboard 增加：

- 当前 Manifest revision；
- 最近生成时间；
- Artifact 总数；
- checksum 覆盖率；
- 缓存覆盖率；
- 冲突数量；
- 最近一次 checksum mismatch。

------

# 18. 测试计划

## 18.1 单元测试

覆盖：

- checksum 算法名称标准化；
- checksum 长度校验；
- 缺少 checksum 的合法序列化；
- Artifact ID 生成；
- URL 与 filename 转义；
- alias 去重；
- 冲突检测；
  -稳定排序；
  -旧 Redis 数据兼容。

## 18.2 Schema 测试

必须验证以下样例：

1. SHA-256 Artifact；
2. 只有 MD5 的 Artifact；
3. 没有 checksum 的 Artifact；
4. 源码包；
5. Linux x86_64 二进制包；
6. Patch；
7. Alias；
8. Cache 命中；
9. Cache 未命中；
10. Legacy/EOL Artifact。

## 18.3 集成测试

启动：

```text
Backend + Redis + 临时缓存目录
```

测试：

```text
运行 Scraper
→ 写入 Redis
→ 构建 Manifest
→ 请求 artifacts.json
→ 请求 /src/{filename}
→ 对比 Manifest 描述
```

## 18.4 故障注入

模拟：

- Redis 中途不可用；
- 写 Manifest 时磁盘满；
- checksum mismatch；
- Scraper 返回重复 filename；
- cache 文件损坏；
- 上游没有 Content-Length；
- 上游返回多次重定向；
- 上游 URL 改变但 filename 不变；
- Manifest 构建过程中进程退出。

要求上一份有效 Manifest 始终可继续读取。

## 18.5 LNMP 契约测试

MirrorOne CI 中保存一份 LNMP 需求清单：

```json
{
  "required_filenames": [
    "nginx-...",
    "php-...",
    "mysql-..."
  ]
}
```

CI 验证：

- 必需文件名存在；
- Artifact ID 唯一；
- `/src/{filename}` 可解析；
- `force_redirect=true` 可解析；
- checksum 缺失不会使 Schema 失败；
- 有 checksum 时格式正确。

------

# 19. 安全要求

## 19.1 URL 限制

Scraper 写入的 URL 必须满足：

- scheme 为 `https` 或明确允许的 legacy `http`；
- 禁止 `file://`；
- 禁止 `ftp://`，除非显式支持；
- 禁止 localhost、环回和私网目标，防止 SSRF；
- GitHub、SourceForge 等重定向必须经过域名策略检查。

## 19.2 文件路径限制

`filename` 必须：

- 不包含 `/`；
- 不包含 `..`；
- 不包含 NUL；
- 不以路径分隔符开头；
- 长度受限；
- 经过 basename 校验。

## 19.3 Manifest 签名

第一版必须提供：

```text
artifacts.json.sha256
```

但该 sidecar 与 Manifest 位于同一服务器，只能用于传输和文件损坏检测，不构成独立信任根。

后续版本可增加：

```text
artifacts.json.sig
```

并由离线维护者密钥签名。该功能不阻塞第一版。

------

# 20. 建议代码改动范围

预计涉及：

```text
backend/app/scrapers/base.py
backend/app/redis_client.py
backend/app/scheduler/jobs.py
backend/app/services/cache_service.py
backend/app/services/redirect_service.py
backend/app/schemas/resource.py
backend/app/routers/redirect.py
backend/app/routers/resources.py
backend/app/main.py
backend/app/manifests/*
backend/tests/manifests/*
frontend/*
docker-compose.yml
README.md
```

------

# 21. 分阶段实施

## PR 1：Manifest Schema 与领域模型

内容：

- 增加 JSON Schema；
- 增加 Pydantic Manifest 模型；
- 定义 Artifact、Source、Mirror、ChecksumMetadata；
- 增加完整样例；
- 暂不接入 Redis。

验收：

- Schema 测试通过；
- checksum 为空的 Artifact 合法；
- MD5-only Artifact 合法。

## PR 2：贯通 checksum 元数据

内容：

- 扩展 Redis 规则；
- Scheduler 写入 checksum；
- 兼容旧 Redis 数据；
- 增加 Redis Schema 版本。

验收：

- PHP Scraper 的 SHA-256 不再丢失；
- 无 checksum 的 Nginx 资源仍正常写入。

## PR 3：Manifest Builder

内容：

- 从 Redis 构建 Artifact；
- 读取版本建议；
- 生成统计；
- 稳定排序；
- 冲突检测。

验收：

- 相同输入产生字节级稳定输出；
- 同名不同 URL 被识别。

## PR 4：原子发布与公开路由

内容：

- 原子写入；
- `.sha256` sidecar；
- ETag；
- Last-Modified；
- 304；
- Last-known-good 保留。

验收：

- 构建失败不会损坏旧 Manifest；
- HTTP 缓存行为正确。

## PR 5：Cache checksum 验证

内容：

- `.part` 文件；
- 上游 checksum 存在时强制验证；
- mismatch quarantine；
- checksum 缺失时兼容缓存；
- 完整性状态写入 Manifest。

验收：

- mismatch 文件不会成为正式缓存；
- 无 checksum 文件仍可正常下载和缓存。

## PR 6：旧接口统一数据源

内容：

- `suggest_versions.txt` 从快照生成；
- `resource.json` 保持旧输出；
- Dashboard 显示 Manifest 状态。

验收：

- 旧脚本无行为变化；
- 新旧版本建议一致。

## PR 7：契约测试与 LNMP Fixture

内容：

- 增加 LNMP Artifact 需求 Fixture；
- 检测精确文件名；
- 检测 force_redirect；
- 生成兼容性报告。

## PR 8：文档与生产迁移

内容：

- README；
- 部署升级说明；
- Redis 迁移说明；
- Manifest 使用说明；
- 故障排查说明。

------

# 22. 完成标准

MirrorOne 的该项改造只有在以下条件全部满足后才算完成：

1. `/manifests/artifacts.json` 稳定可访问；
2. Schema 版本明确；
3. Manifest 为原子快照；
4. Scraper 中发现的 checksum 不再丢失；
5. 没有上游 checksum 的资源仍可正常发布；
6. 上游 checksum 与 MirrorOne 自计算摘要语义分离；
7. Cache 模式在 checksum 存在时强制验证；
8. checksum mismatch 文件不会进入正式缓存；
9. `/src/{filename}` 行为不变；
10. `force_redirect=true` 行为不变；
11. `suggest_versions.txt` 行为不变；
12. 旧 Redis 数据无需清空即可升级；
13. 同名制品冲突不会被静默覆盖；
14. LNMP 契约测试能够输出完整缺失资源报告；
15. Manifest 构建失败时继续提供上一份有效快照。
