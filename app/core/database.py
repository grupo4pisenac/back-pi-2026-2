import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

RAW_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:adminpassword@localhost:5432/agrotech_db")

# Garante URL síncrona para o engine síncrono (compatibilidade com scheduler e código legado)
SYNC_DATABASE_URL = RAW_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Garante URL assíncrona com asyncpg para o engine assíncrono
if SYNC_DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    ASYNC_DATABASE_URL = SYNC_DATABASE_URL

# Engine e Sessão Síncrona (usado pelo scheduler do ThingSpeak)
engine = create_engine(SYNC_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Engine e Sessão Assíncrona (usado pelas rotas da API assíncrona)
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Dependência assíncrona padrão para FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Dependência síncrona para rotas legadas
def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()