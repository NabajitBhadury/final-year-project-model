"""Uvicorn entry point for the FarmEasy FastAPI backend."""

from __future__ import annotations

import argparse

import uvicorn

from .config import get_settings


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="FarmEasy FastAPI backend")
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--reload", action="store_true", default=settings.reload)
    args = parser.parse_args()

    uvicorn.run(
        "server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
