# Production FastAPI Skeleton Project

## Project Structure
```
fastapi-skeleton/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── database.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       ├── users.py
│   │   │       └── health.py
│   │   └── graphql/
│   │       ├── __init__.py
│   │       ├── schema.py
│   │       ├── types.py
│   │       └── resolvers.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   └── user_service.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   │   ├── __init__.py
│   │   └── test_users.py
│   └── test_services/
│       ├── __init__.py
│       └── test_user_service.py
├── alembic/
│   ├── versions/
│   ├── env.py
│   ├── script.py.mako
│   └── alembic.ini
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── deployment/
│   ├── k8s/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   └── scripts/
│       ├── deploy.sh
│       └── health_check.sh
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
├── .env.example
├── .env.dev
├── .env.uat
├── .env.prod
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── README.md
└── Makefile
```

## Core Files

### 1. requirements.txt
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
redis==5.0.1
strawberry-graphql[fastapi]==0.214.1
alembic==1.13.1
pydantic[email]==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
structlog==23.2.0
prometheus-client==0.19.0
httpx==0.25.2
```

### 2. requirements-dev.txt
```
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1
pre-commit==3.6.0
```

### 3. app/config/settings.py
```python
from pydantic import BaseSettings, PostgresDsn, validator
from typing import Optional, Any, Dict
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "FastAPI Skeleton"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # API
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000"]
    
    class Config:
        case_sensitive = True
        env_file = f".env.{os.getenv('ENVIRONMENT', 'dev')}"

settings = Settings()
```

### 4. app/config/database.py
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .settings import settings

engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 5. app/core/logging.py
```python
import structlog
import logging
import sys
from .settings import settings

def configure_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    
    if settings.LOG_FORMAT == "json":
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            logger_factory=structlog.WriteLoggerFactory(file=sys.stdout),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=[
                structlog.dev.ConsoleRenderer(colors=True)
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            logger_factory=structlog.WriteLoggerFactory(file=sys.stdout),
            cache_logger_on_first_use=True,
        )

def get_logger(name: str = None):
    return structlog.get_logger(name)
```

### 6. app/core/exceptions.py
```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
import structlog

logger = structlog.get_logger(__name__)

class CustomHTTPException(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: str = None):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code

class DatabaseException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class CacheException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        error_code=exc.error_code,
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code or "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        }
    )

async def database_exception_handler(request: Request, exc: DatabaseException):
    logger.error("Database exception occurred", message=exc.message, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Internal database error occurred"
            }
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unexpected exception occurred", exception=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )
```

### 7. app/services/cache.py
```python
import redis.asyncio as redis
import json
from typing import Any, Optional
from ..config.settings import settings
from ..core.exceptions import CacheException
import structlog

logger = structlog.get_logger(__name__)

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            raise CacheException(f"Failed to get cache key: {key}")
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            serialized_value = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            raise CacheException(f"Failed to set cache key: {key}")
    
    async def delete(self, key: str) -> bool:
        try:
            result = await self.redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            raise CacheException(f"Failed to delete cache key: {key}")
    
    async def close(self):
        await self.redis.close()

cache_service = CacheService()
```

### 8. app/models/user.py
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ..config.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 9. app/api/v1/endpoints/users.py
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
import structlog

from ...config.database import get_db
from ...models.user import User
from ...services.cache import cache_service

logger = structlog.get_logger(__name__)
router = APIRouter()

class UserCreate(BaseModel):
    email: str
    full_name: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    
    class Config:
        from_attributes = True

@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    cache_key = f"users:skip:{skip}:limit:{limit}"
    cached_users = await cache_service.get(cache_key)
    
    if cached_users:
        logger.info("Retrieved users from cache", count=len(cached_users))
        return cached_users
    
    result = await db.execute(
        "SELECT * FROM users LIMIT :limit OFFSET :skip",
        {"limit": limit, "skip": skip}
    )
    users = result.fetchall()
    
    user_list = [UserResponse.from_orm(user) for user in users]
    await cache_service.set(cache_key, [user.dict() for user in user_list])
    
    logger.info("Retrieved users from database", count=len(user_list))
    return user_list

@router.post("/users", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        db_user = User(**user.dict())
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        logger.info("User created", user_id=db_user.id, email=user.email)
        return UserResponse.from_orm(db_user)
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create user", error=str(e))
        raise HTTPException(status_code=400, detail="Failed to create user")
```

### 10. app/api/graphql/schema.py
```python
import strawberry
from typing import List, Optional
from .types import User, UserInput
from .resolvers import get_users, create_user

@strawberry.type
class Query:
    users: List[User] = strawberry.field(resolver=get_users)

@strawberry.type
class Mutation:
    create_user: User = strawberry.field(resolver=create_user)

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

### 11. app/main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from contextlib import asynccontextmanager

from .config.settings import settings
from .core.logging import configure_logging
from .core.exceptions import (
    CustomHTTPException,
    DatabaseException,
    custom_http_exception_handler,
    database_exception_handler,
    general_exception_handler
)
from .api.v1.router import api_router
from .api.graphql.schema import schema
from .services.cache import cache_service

configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await cache_service.close()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(CustomHTTPException, custom_http_exception_handler)
app.add_exception_handler(DatabaseException, database_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# GraphQL
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
```

### 12. Docker Configuration

#### docker/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker/docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=dev
    depends_on:
      - postgres
      - redis
    volumes:
      - ..:/app
    
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: fastapi_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 13. CI/CD Configuration

#### .github/workflows/ci.yml
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        black --check .
        isort --check-only .
        flake8 .
    
    - name: Run type checking
      run: mypy app/
    
    - name: Run tests
      run: pytest --cov=app --cov-report=xml
      env:
        DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
        SECRET_KEY: test-secret-key
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### 14. Environment Configuration

#### .env.example
```
# Application
APP_NAME=FastAPI Skeleton
VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-db-password
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fastapi_prod

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=300

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# CORS
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
```

### 15. Makefile
```makefile
.PHONY: install dev test lint format clean build deploy

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest --cov=app tests/

lint:
	black --check .
	isort --check-only .
	flake8 .
	mypy app/

format:
	black .
	isort .

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

build:
	docker build -f docker/Dockerfile -t fastapi-skeleton .

deploy-dev:
	docker-compose -f docker/docker-compose.yml up -d

deploy-prod:
	docker-compose -f docker/docker-compose.prod.yml up -d
```

## Key Features Implemented:

1. **Database Connections**: SQLAlchemy with async PostgreSQL support
2. **Logging**: Structured logging with configurable formats
3. **Exception Handling**: Custom exception classes and handlers
4. **Deployment**: Docker, Docker Compose, and GitHub Actions CI/CD
5. **REST API**: FastAPI with proper routing and dependency injection
6. **GraphQL**: Strawberry GraphQL integration
7. **Multi-environment**: Environment-specific configuration files
8. **Configurable Settings**: Pydantic settings with validation

This skeleton provides a solid foundation for production applications with industry best practices.
