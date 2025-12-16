# TIMIMA

A production-ready FastAPI backend application built with modern Python, designed for scalability, security, and maintainability.

## Overview

TIMIMA is a modular, enterprise-grade web API service following clean architecture principles. It provides a robust foundation for building scalable RESTful APIs with comprehensive authentication, authorization, and monitoring capabilities.

### Key Features

- **Modern Async Architecture**: Built on FastAPI with full async/await support
- **Production-Grade Security**: JWT authentication, rate limiting, and comprehensive security headers
- **Scalable Design**: Connection pooling, Redis caching, and read-replica support
- **Modular Structure**: Self-contained feature modules with clear separation of concerns
- **Observability**: Integrated logging, metrics (Prometheus), and distributed tracing (OpenTelemetry)
- **Type-Safe**: Full type hint coverage with Pydantic validation
- **Developer-Friendly**: Auto-loading routers, hot reload, and comprehensive test fixtures

## Technology Stack

### Core Framework
- **FastAPI 0.124.2+**: Modern async web framework
- **Python 3.14**: Latest Python with type hints
- **Uvicorn with uvloop**: High-performance ASGI server
- **Pydantic 2.12.5+**: Data validation and settings management

### Database
- **PostgreSQL with pgvector**: Primary database with vector search support
- **SQLAlchemy 2.0.45+**: Async ORM
- **asyncpg 0.31.0+**: PostgreSQL async driver
- **Alembic 1.17.2+**: Database migrations

### Caching & Sessions
- **Redis 7.1.0+**: Caching, session management, and rate limiting
- **Hiredis**: High-performance Redis client

### Security
- **python-jose**: JWT token generation and verification
- **passlib with bcrypt**: Password hashing
- **argon2-cffi**: Alternative password hashing algorithm
- **cryptography 44.0.0+**: Cryptographic operations

### Monitoring & Observability
- **Prometheus client**: Metrics collection
- **Sentry SDK**: Error tracking and monitoring
- **OpenTelemetry**: Distributed tracing for FastAPI, SQLAlchemy, and Redis

### Development & Testing
- **pytest + pytest-asyncio**: Testing framework with async support
- **pytest-cov**: Code coverage reporting
- **mypy**: Static type checking
- **ruff**: Fast linting and formatting
- **pre-commit**: Git hooks for code quality
- **locust**: Load testing

## Project Structure

```
timima/
├── src/
│   ├── core/                     # Core infrastructure
│   │   ├── configs/              # Configuration management
│   │   ├── databases/            # Database abstractions
│   │   ├── security/             # Security & authentication
│   │   ├── middlewares/          # HTTP middlewares
│   │   ├── exceptions/           # Error handling
│   │   ├── loggings/             # Logging infrastructure
│   │   ├── routers/              # Auto-loading router system
│   │   ├── controllers/          # Base controller patterns
│   │   └── utils/                # Utilities
│   │
│   ├── modules/                  # Business feature modules
│   │   ├── auth/                 # Authentication module
│   │   │   ├── controller.py     # API endpoints
│   │   │   ├── service.py        # Business logic
│   │   │   ├── repository.py     # Data access
│   │   │   ├── models.py         # Database models
│   │   │   ├── schemas.py        # Request/response schemas
│   │   │   └── dependencies.py   # DI factories
│   │   │
│   │   └── user/                 # User management module
│   │       └── [same structure]
│   │
│   └── app.py                    # Application factory
│
├── alembic/                      # Database migrations
├── tests/                        # Test suite
│   ├── units/                    # Unit tests
│   ├── features/                 # Feature/E2E tests
│   └── conftest.py               # Test fixtures
├── docker/                       # Docker configurations
├── logs/                         # Application logs
├── main.py                       # Entry point
└── pyproject.toml                # Project metadata & dependencies
```

### Architecture Patterns

- **Module-based Architecture**: Each feature is a self-contained module
- **Repository Pattern**: Data access abstraction layer
- **Service Layer**: Business logic separated from controllers
- **Dependency Injection**: FastAPI's DI system with factory functions
- **Controller Pattern**: Standardized API response handling

## Getting Started

### Prerequisites

- Python 3.14+
- PostgreSQL 16+ (with pgvector extension)
- Redis 7.1+
- UV package manager (recommended) or pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd timima
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   # Using UV (recommended)
   uv sync

   # Or using pip
   pip install -e .
   ```

4. **Start infrastructure services**
   ```bash
   docker-compose up -d
   ```

5. **Run database migrations**
   ```bash
   uv run alembic upgrade head
   ```

6. **Start the application**
   ```bash
   # Development mode
   uv run uvicorn main:app --reload

   # Production mode
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

The API will be available at `http://localhost:8000`

### Development Setup

1. **Install development dependencies**
   ```bash
   uv sync --all-extras
   ```

2. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

3. **Run tests**
   ```bash
   # Run all tests
   uv run pytest

   # Run with coverage
   uv run pytest --cov=src --cov-report=html

   # Run specific test types
   uv run pytest -m units
   uv run pytest -m features
   ```

4. **Code quality checks**
   ```bash
   # Linting and formatting
   ruff check .
   ruff format .

   # Type checking
   mypy src/
   ```

## Configuration

### Environment Variables

Key configuration options (see [.env.example](.env.example) for full list):

```env
# Application
APP_NAME=TIMIMA
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=timima
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
PASSWORD_MIN_LENGTH=8
PASSWORD_BCRYPT_ROUNDS=12
RATE_LIMIT_PER_MINUTE=60
```

### Database Configuration

- **Connection Pooling**: 20 connections (configurable)
- **Pool Overflow**: 40 additional connections
- **Pool Recycle**: 1800 seconds
- **Health Checks**: Pre-ping enabled

### Redis Configuration

- **Timeout**: 5 seconds
- **Max Connections**: 50
- **Eviction Policy**: allkeys-lru (in Docker)

## API Documentation

### Endpoints

Once the application is running, access the interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Core Modules

#### Authentication Module ([/auth](src/modules/auth/))

- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `POST /auth/logout` - Token revocation
- `POST /auth/refresh` - Token refresh with rotation
- `GET /auth/me` - Get current user info
- `GET /auth/sessions` - List active sessions
- `DELETE /auth/sessions/{id}` - Revoke specific session
- `POST /auth/revoke-all` - Logout from all devices

**Features**:
- JWT-based authentication (access + refresh tokens)
- Token blacklisting via Redis
- Refresh token rotation with family tracking
- Multi-device session management
- Account lockout after failed login attempts

#### User Module ([/users](src/modules/user/))

- `GET /users/me` - Current user profile
- `PATCH /users/me` - Update own profile
- `POST /users/me/change-password` - Password change
- `GET /users` - List users (admin only)
- `POST /users` - Create user (admin only)
- `GET /users/{id}` - Get user details (admin only)
- `PATCH /users/{id}` - Update user (admin only)
- `DELETE /users/{id}` - Delete user (admin only)
- `POST /users/{id}/activate|deactivate` - Account management (admin)

**Features**:
- Role-based access control (user, admin)
- Email uniqueness validation
- Password strength requirements
- Account activation/deactivation
- Pagination support

### Health Checks

- `GET /health` - Comprehensive health check
- `GET /health/database` - Database status
- `GET /health/redis` - Redis status

## Security Features

### Authentication & Authorization

- **JWT Tokens**: Access tokens (15-60 min) and refresh tokens (7-30 days)
- **Token Security**: JWT ID (jti), blacklisting, token family tracking
- **Password Security**: Bcrypt hashing (12 rounds), minimum 8 characters
- **Account Protection**: Lockout after 5 failed attempts (15 minutes)

### Security Middleware

- **Rate Limiting**: 60 requests/minute per IP (configurable)
- **CORS**: Strict origin validation
- **Security Headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **Request Tracking**: Unique request ID per request

### Data Protection

- **Sensitive Data Masking**: Automatic masking in logs
- **Timezone-Aware**: All timestamps stored in UTC
- **Input Validation**: Comprehensive Pydantic schemas
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

## Database Migrations

### Creating a New Migration

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "Description of changes"

# Create empty migration
uv run alembic revision -m "Description of changes"
```

### Applying Migrations

```bash
# Upgrade to latest version
uv run alembic upgrade head

# Upgrade by one version
uv run alembic upgrade +1

# Downgrade by one version
uv run alembic downgrade -1

# Check current version
uv run alembic current

# View migration history
uv run alembic history
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test categories
uv run pytest -m units           # Unit tests only
uv run pytest -m features        # Feature tests only
uv run pytest -m integration     # Integration tests only

# Run specific test file
uv run pytest tests/units/test_auth.py

# Run with verbose output
uv run pytest -v
```

### Test Coverage

View coverage report:
```bash
# Generate HTML report
uv run pytest --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html
```

### Load Testing

```bash
# Install locust
uv pip install locust

# Run load tests
locust -f tests/load/locustfile.py
```

## Deployment

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **View logs**
   ```bash
   docker-compose logs -f app
   ```

3. **Stop services**
   ```bash
   docker-compose down
   ```

### Production Deployment

#### Environment Setup

1. Set `ENVIRONMENT=production` in `.env`
2. Use strong `JWT_SECRET_KEY` (minimum 32 characters)
3. Configure production database and Redis instances
4. Set up reverse proxy (nginx) with HTTPS
5. Configure monitoring (Sentry, Prometheus)

#### Running in Production

```bash
# Using uvicorn with multiple workers
uv run uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-config logging_config.json

# Or using gunicorn
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

#### Production Checklist

- [ ] Set strong JWT secret key
- [ ] Configure production database with connection pooling
- [ ] Set up Redis with persistence (RDB + AOF)
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure CORS with specific allowed origins
- [ ] Set up log aggregation and monitoring
- [ ] Configure Sentry for error tracking
- [ ] Set up Prometheus metrics collection
- [ ] Enable rate limiting appropriate for your use case
- [ ] Regular database backups
- [ ] Health check monitoring
- [ ] Resource limits (memory, CPU) for containers

### Monitoring & Logging

#### Logging

Logs are written to:
- Console (colored in development, JSON in production)
- File: `logs/timima.log` (daily rotation, 30-day retention)
- Error log: `logs/timima_error.log`

#### Metrics

Prometheus metrics available at `/metrics`:
- Request count and duration
- Database query performance
- Redis cache hit/miss rates
- Active session count

#### Error Tracking

Sentry integration for:
- Unhandled exceptions
- Request context capture
- User context tracking
- Performance monitoring

## Contributing

### Development Workflow

1. Create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and ensure tests pass
   ```bash
   uv run pytest
   ```

3. Run code quality checks
   ```bash
   ruff check .
   ruff format .
   mypy src/
   ```

4. Commit your changes (pre-commit hooks will run)
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

5. Push and create a pull request
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Write docstrings for public APIs
- Keep functions focused and small
- Use meaningful variable names
- Add tests for new features

### Adding a New Module

1. Create module directory in `src/modules/`
2. Follow the standard structure:
   - `controller.py` - API endpoints
   - `service.py` - Business logic
   - `repository.py` - Data access
   - `models.py` - Database models
   - `schemas.py` - Request/response schemas
   - `dependencies.py` - DI factories

3. The router will be auto-loaded on startup

## Performance Optimization

### Database Optimization

- **Connection Pooling**: Pre-configured with optimal settings
- **Query Optimization**: Use eager loading to prevent N+1 queries
- **Indexing**: Indexes on frequently queried columns
- **Read Replicas**: Configure `DATABASE_REPLICA_HOST` for read scaling

### Caching Strategy

- **Redis Caching**: Token blacklist, session data, rate limiting
- **Response Caching**: Implement for frequently accessed, static data
- **Cache Invalidation**: Automatic on data updates

### Performance Monitoring

- Track slow queries (>100ms logged in PostgreSQL)
- Monitor request duration via Prometheus
- Use OpenTelemetry for distributed tracing
- Profile with `cProfile` for bottleneck identification

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection settings in .env
cat .env | grep DATABASE_

# Test connection
docker-compose exec postgres psql -U postgres -d timima
```

**Redis Connection Errors**
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
```

**Migration Errors**
```bash
# Check current migration status
uv run alembic current

# View pending migrations
uv run alembic history

# Rollback last migration
uv run alembic downgrade -1
```

**Import Errors**
```bash
# Reinstall dependencies
uv sync --reinstall

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
```

## License

[Add your license here]

## Support

For issues and questions:
- Create an issue in the repository
- Contact the development team

## Acknowledgments

Built with FastAPI and the Python async ecosystem.
