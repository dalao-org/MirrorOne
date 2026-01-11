# Oneinstack Mirror Generator v2.0

A dynamic mirror generator for OneinStack software packages. This version replaces the static GitHub Actions + Cloudflare Pages approach with a FastAPI backend, Next.js frontend, and Redis-backed redirect rules.

## 🚀 Features

- **Dynamic Redirects**: Real-time redirect rules stored in Redis
- **Admin Dashboard**: Web-based management interface
- **Scheduled Scraping**: Automatic background updates via APScheduler
- **Standardized Scrapers**: Modular scraper architecture for easy extension
- **Docker Deployment**: One-command deployment with Docker Compose

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   OneinStack    │────▶│    FastAPI      │────▶│     Redis       │
│    Scripts      │     │    Backend      │     │  (Redirect DB)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │    Next.js      │
                        │    Frontend     │
                        └─────────────────┘
```

## 📦 Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Backend | FastAPI | 0.115+ |
| Frontend | Next.js (Turbopack) | 16.1.1 |
| Database | SQLite | - |
| Cache | Redis | 8.4 |
| Runtime | Python | 3.14 |
| ORM | SQLAlchemy | 2.x |
| Validation | Pydantic | 2.x |

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Deployment

1. Clone the repository:
   ```bash
   git clone https://github.com/dalao-org/oneinstack-mirror-generator.git
   cd oneinstack-mirror-generator
   ```

2. Configure environment files:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

3. Edit `backend/.env` with your settings:
   ```env
   SECRET_KEY=your-super-secret-key
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your-secure-password
   ```

4. Start the services:
   ```bash
   docker-compose up -d
   ```

5. Access the dashboard at `http://localhost:3000`

## 📁 Project Structure

```
oneinstack-mirror-generator/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # SQLite connection
│   │   ├── redis_client.py    # Redis operations
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── routers/           # API endpoints
│   │   ├── services/          # Business logic
│   │   ├── scrapers/          # Package scrapers
│   │   └── scheduler/         # Background tasks
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Next.js frontend
│   ├── app/                   # App Router pages
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔌 API Endpoints

### Public Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/src/{filename}` | Redirect to download URL |
| GET | `/suggest_versions.txt` | Version suggestions |

### Protected Endpoints (require JWT)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Admin login |
| GET | `/api/settings` | Get all settings |
| PUT | `/api/settings/{key}` | Update setting |
| GET | `/api/resources` | List all resources |
| POST | `/api/scraper/run` | Trigger full scrape |
| GET | `/api/scraper/logs` | View scrape logs |

## 🔧 Adding a New Scraper

1. Create a new file in `backend/app/scrapers/`:

   ```python
   # backend/app/scrapers/mypackage.py
   from .base import BaseScraper, Resource, VersionMeta, ScrapeResult
   from .registry import registry
   
   @registry.register("mypackage")
   class MyPackageScraper(BaseScraper):
       async def scrape(self) -> ScrapeResult:
           result = ScrapeResult(scraper_name=self.name)
           
           # Your scraping logic here
           response = await self.http_client.get("https://example.com")
           # Parse response and add resources
           
           result.resources.append(Resource(
               file_name="mypackage-1.0.0.tar.gz",
               url="https://example.com/download/mypackage-1.0.0.tar.gz",
               version="1.0.0",
           ))
           
           result.success = True
           return result
   ```

2. Import it in `backend/app/scrapers/__init__.py`:
   ```python
   from . import mypackage
   ```

## ⚙️ Configuration

### Backend Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `github_api_token` | string | "" | GitHub API token for rate limits |
| `php_accepted_versions` | json | ["8.1", "8.2", "8.3", "8.4"] | PHP versions to track |
| `scrape_interval_hours` | int | 6 | Hours between auto-scrapes |
| `enable_auto_scrape` | bool | true | Enable scheduled scraping |

## 🔒 Security

- JWT tokens expire after 24 hours
- Passwords are hashed with bcrypt
- API docs are disabled in production
- CORS is configured per environment

## 📊 Monitoring

- Health check: `GET /health`
- Scrape logs: Available in dashboard
- Scheduler status: Available via API

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your scraper or improvement
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Credits

- Original project by [dalao-org](https://github.com/dalao-org)
- v2.0 refactor for improved reliability and maintainability
