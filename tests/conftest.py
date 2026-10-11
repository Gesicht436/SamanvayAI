"""Pytest configuration and Windows event loop setup for async psycopg3."""

import asyncio
import sys

# psycopg3 async requires WindowsSelectorEventLoopPolicy on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
