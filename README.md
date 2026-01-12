# MirrorOne

<p align="center">
  <img src="frontend/public/OneMirror-Light.png" alt="OneMirror Logo" width="200">
</p>

<p align="center">
  <a href="https://mirror.dal.ao"><img src="https://img.shields.io/badge/Demo-演示站点-brightgreen" alt="Demo"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://github.com/dalao-org/MirrorOne"><img src="https://img.shields.io/github/stars/dalao-org/MirrorOne?style=social" alt="GitHub Stars"></a>
</p>

> 主流 Linux 服务器软件镜像缓存工具，轻松搭建稳定、快速、可信的私有镜像源
>
> *A caching mirror tool for popular Linux server software. Build your own fast, reliable, and trustworthy mirror.*

## 🚀 功能特性

- **动态重定向** - 实时生成的重定向规则，存储于 Redis 中
- **双镜像模式**
  - `redirect` 重定向模式：302 跳转到原始源，提供最安全的保证
  - `cache` 缓存模式：本地缓存文件，为特殊网络（如本地局域网）提供镜像中转支持
- **Web 管理后台** - 直观的 Dashboard，管理资源和设置
- **定时自动抓取** - 基于 APScheduler 的后台任务，定期更新资源链接
- **模块化爬虫架构** - 标准化的 Scraper 基类，轻松扩展新软件包
- **Docker 一键部署** - 使用 Docker Compose 快速部署

### 兼容的脚本

- Oneinstack
- [linuxeye/lnmp](https://github.com/linuxeye/lnmp)

---

## 🧩 支持的软件包

### Web 服务器
| 软件包 | 来源 |
|--------|------|
| Nginx | nginx.org |
| Apache HTTP Server (httpd) | archive.apache.org |
| OpenResty | openresty.org |
| Tengine | GitHub |

### 数据库
| 软件包 | 来源 |
|--------|------|
| MySQL | dev.mysql.com |
| MariaDB | mariadb.org |
| PostgreSQL | ftp.postgresql.org |
| Redis | redis.io |

### PHP 相关
| 软件包 | 来源 |
|--------|------|
| PHP | php.net |
| phpMyAdmin | phpmyadmin.net |
| PHP 扩展 (apcu, igbinary, redis, swoole, yaf...) | pecl.php.net |
| Phalcon (cphalcon) | GitHub |
| XCache | GitHub |

### 库和工具
| 软件包 | 来源 |
|--------|------|
| cURL | curl.se |
| OpenSSL | openssl.org |
| nghttp2 | GitHub |
| APR / APR-util | apache.org |
| ImageMagick | imagemagick.org |
| FreeType | sourceforge.net |
| libiconv | gnu.org |
| Boost | boost.io |
| Bison | gnu.org |

### 语言运行时
| 软件包 | 来源 |
|--------|------|
| Python | python.org |
| pip | pypi.org |

### 缓存组件
| 软件包 | 来源 |
|--------|------|
| Memcached | memcached.org |

### 安全与工具
| 软件包 | 来源 |
|--------|------|
| Fail2ban | GitHub |
| CA 证书 (cacert) | curl.se |
| acme.sh | GitHub |
| Pure-FTPd | GitHub |
| htop | GitHub |

### Nginx 模块
| 软件包 | 来源 |
|--------|------|
| lua-nginx-module | GitHub |
| ngx_devel_kit | GitHub |

### 其他 GitHub 项目
| 软件包 | 来源 |
|--------|------|
| jemalloc | GitHub |
| lua-resty-core | GitHub (OpenResty) |
| lua-resty-lrucache | GitHub (OpenResty) |
| luajit2 | GitHub (OpenResty) |
| lua-cjson | GitHub (OpenResty) |
| gperftools | GitHub |
| ICU4C | GitHub |
| libzip | GitHub |
| libsodium | GitHub |
| Argon2 | GitHub |
| libevent | GitHub |
| Oniguruma | GitHub |

---

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- Git

### 部署步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/dalao-org/MirrorOne.git
   cd MirrorOne
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   ```

3. **编辑 `.env` 文件**（参照下方环境变量说明）

4. **启动服务**
   ```bash
   docker-compose up -d
   ```

5. **访问管理后台**
   - 前端 Dashboard: `http://localhost:3000`
   - 后端 API: `http://localhost:7980`

### 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_NAME` | 应用名称 | `MirrorOne` |
| `DEBUG` | 调试模式 | `false` |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite+aiosqlite:///./data/app.db` |
| `REDIS_URL` | Redis 连接地址 | `redis://redis:6379/0` |
| `SECRET_KEY` | JWT 密钥 (⚠️ 生产环境必须修改) | - |
| `JWT_ALGORITHM` | JWT 算法 | `HS256` |
| `JWT_EXPIRE_HOURS` | JWT 过期时间（小时） | `24` |
| `ADMIN_USERNAME` | 管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 管理员密码 (⚠️ 生产环境必须修改) | - |
| `CORS_ORIGINS` | 允许的跨域来源 | `["http://localhost:3000"]` |
| `NEXT_PUBLIC_API_URL` | 前端访问后端的 URL | `http://backend:8000` |
| `TUNNEL_TOKEN` | Cloudflare Tunnel Token（可选） | - |

### Cloudflare Tunnel 配置（可选）

如果你想通过 Cloudflare Tunnel 暴露服务：

1. 在 Cloudflare Zero Trust Dashboard 中创建 Tunnel
2. 获取 Tunnel Token
3. 在 `.env` 中设置 `TUNNEL_TOKEN`
4. 重启服务

---

## 本地开发

### 不使用 Docker 启动

#### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

### 添加新 Scraper

1. 在 `backend/app/scrapers/` 目录下创建新文件：

   ```python
   # backend/app/scrapers/mypackage.py
   from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
   from .registry import registry
   
   @registry.register("mypackage")
   class MyPackageScraper(BaseScraper):
       async def scrape(self) -> ScrapeResult:
           result = ScrapeResult(scraper_name=self.name)
           
           # 你的抓取逻辑
           response = await self.http_client.get("https://example.com")
           # 解析响应并添加资源
           
           result.resources.append(Resource(
               file_name="mypackage-1.0.0.tar.gz",
               url="https://example.com/download/mypackage-1.0.0.tar.gz",
               version="1.0.0",
           ))
           
           result.success = True
           return result
   ```

2. 在 `backend/app/scrapers/__init__.py` 中导入：
   ```python
   from . import mypackage
   ```

---

## 常见问题

### OneinStack 如何使用此镜像？

修改 OneinStack 的 `options.conf` 文件，将 `mirror_link` 设置为你的镜像地址：

```conf
mirror_link="https://your-mirror-domain.com"
```

### 如何切换镜像模式？

登录管理后台 → Settings → 修改 `mirror_mode` 设置：
- `redirect`: 302 重定向到原始下载地址
- `cache`: 从本地缓存提供文件（需要预先下载）

### 如何手动触发抓取？

登录管理后台 → Dashboard → 点击 "Run Full Scrape" 按钮

### 如何查看抓取日志？

登录管理后台 → Dashboard → Scrape Logs 区域

---

## 🔒 安全说明

- JWT Token 默认 24 小时过期
- 密码使用 bcrypt 加密存储
- 生产环境请务必修改 `SECRET_KEY` 和 `ADMIN_PASSWORD`
- 生产环境建议禁用 API 文档（设置 `DEBUG=false`）

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/new-scraper`)
3. 提交更改 (`git commit -am 'Add new scraper'`)
4. 推送到分支 (`git push origin feature/new-scraper`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

