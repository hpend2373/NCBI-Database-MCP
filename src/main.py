"""
Main entry point - choose between standalone or queue-enabled BLAST server
"""
import asyncio
import os
import argparse
from .server import BlastServer
from .blast_with_queue import BlastServerWithQueue


async def main():
    parser = argparse.ArgumentParser(description="BLAST MCP Server")
    parser.add_argument(
        "--mode",
        choices=["local", "queue"],
        default="local",
        help="Run mode: local (immediate) or queue (async jobs)"
    )
    parser.add_argument(
        "--queue-url",
        default="http://localhost:8000",
        help="Queue API URL (only used in queue mode)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "queue":
        print(f"🔄 Starting BLAST server with queue support ({args.queue_url})")
        server = BlastServerWithQueue(queue_url=args.queue_url)
    else:
        print("⚡ Starting standalone BLAST server (immediate results)")
        server = BlastServer()
    
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())