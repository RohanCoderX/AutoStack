import sys
import subprocess
import os
import asyncpg
import asyncio

async def health_check():
    """Health check for Docker container"""
    try:
        # Check Terraform
        result = subprocess.run(["terraform", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Health check failed: Terraform not available")
            sys.exit(1)
        
        # Check AWS CLI
        result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Health check failed: AWS CLI not available")
            sys.exit(1)
        
        # Check database connection
        if os.getenv("DATABASE_URL"):
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