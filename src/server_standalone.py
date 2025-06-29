"""
Standalone BLAST server - no queue dependency
Works completely locally with immediate results
"""
from .server import BlastServer


async def main():
    # Original server - runs BLAST locally and returns results immediately
    server = BlastServer()
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())