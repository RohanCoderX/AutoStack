import asyncpg
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Async PostgreSQL database manager"""
    
    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL")
        self.pool = None
    
    async def connect(self):
        """Create database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return data"""
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict]:
        """Fetch single row"""
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, *args) -> List[Dict]:
        """Fetch multiple rows"""
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def fetch_val(self, query: str, *args) -> Any:
        """Fetch single value"""
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)