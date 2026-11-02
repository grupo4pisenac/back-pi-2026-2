
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

RAW_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:adminpassword@localhost:5432/agrotech_db"
)

print("DATABASE_URL existe:", bool(RAW_DATABASE_URL))
print("DATABASE_URL começa com postgresql://:", RAW_DATABASE_URL.startswith("postgresql://"))
print("DATABASE_URL tamanho:", len(RAW_DATABASE_URL))

# O projeto utiliza psycopg 3 para conexões síncronas
SYNC_DATABASE_URL = RAW_DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg://"
)
if SYNC_DATABASE_URL.startswith("postgresql://"):
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )

# O projeto utiliza asyncpg para conexões assíncronas
ASYNC_DATABASE_URL = RAW_DATABASE_URL.replace(
    "postgresql+psycopg://", "postgresql+asyncpg://"
)
if ASYNC_DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )

# SSL ativado somente no ambiente Azure
DB_SSL = os.getenv("DB_SSL", "false").lower() == "true"

sync_connect_args = {"sslmode": "require"} if DB_SSL else {}
async_connect_args = {"ssl": True} if DB_SSL else {}

engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    connect_args=sync_connect_args
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    connect_args=async_connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
