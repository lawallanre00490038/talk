from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from ssl import create_default_context, CERT_REQUIRED
from typing import Optional, AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

load_dotenv()


_async_engine = None
_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None

def _get_ssl_context():
    """Create SSL context for secure PostgreSQL connections."""
    ssl_context = create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = CERT_REQUIRED 
    return ssl_context


def _get_ssl_context_none():
    pass

def get_async_engine():
    """Get or create the async engine (lazy initialization)."""
    global _async_engine
    if _async_engine is None:
        DATABASE_URL = settings.DATABASE_URL_ASYNC
        
        _async_engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=900,
            pool_timeout=30,
            connect_args={
                "prepared_statement_cache_size": 0,
                "ssl": _get_ssl_context_none(),
                "timeout": 60,
                "command_timeout": 300,
                "server_settings": {
                    "tcp_keepalives_idle": "30",
                    "tcp_keepalives_interval": "10",
                    "tcp_keepalives_count": "3",
                },
            },
        )
        logger.info("✅ Async engine created")
    return _async_engine


def get_async_session_maker(force_new: bool = False) -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session maker.
    If `force_new=True`, always create a new engine + session maker.
    This is useful for Celery workers or standalone async scripts
    where the global engine might be stale or already disposed.
    """
    global _async_engine, _async_session_maker

    if force_new:
        logger.warning("⚙️  Forcing creation of a fresh async engine and session maker...")
        DATABASE_URL = settings.DATABASE_URL_ASYNC

        new_engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=900,
            pool_timeout=30,
            connect_args={
                "prepared_statement_cache_size": 0,
                "ssl": _get_ssl_context_none(),
                "timeout": 60,
                "command_timeout": 300,
                "server_settings": {
                    "tcp_keepalives_idle": "30",
                    "tcp_keepalives_interval": "10",
                    "tcp_keepalives_count": "3",
                },
            },
        )

        return async_sessionmaker(
            bind=new_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    # Default (re-use global)
    if _async_session_maker is None:
        engine = get_async_engine()
        _async_session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        logger.info("✅ Async session maker created")

    return _async_session_maker



async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting an async session."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# Create tables
async def create_tables():
    """Create all tables asynchronously."""
    try:
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise