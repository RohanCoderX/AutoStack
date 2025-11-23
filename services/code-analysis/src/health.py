import asyncio
import asyncpg
import os
import sys

async def health_check():
    """Health check for Docker container"""
    try:
        # Check database connection
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        await conn.execute("SELECT 1")
        await conn.close()
        
        print("Health check passed")
        sys.exit(0)
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(health_check())