"""Standalone MCP entry point.

Run with:
    python -m server.mcp_server --transport streamable-http
    python -m server.mcp_server --transport stdio
"""

from __future__ import annotations

import argparse

from .mcp_tools import create_mcp_server


def main() -> None:
    parser = argparse.ArgumentParser(description="FarmEasy MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport to use. Use streamable-http for remote clients.",
    )
    args = parser.parse_args()

    path = "/mcp" if args.transport == "streamable-http" else "/"
    mcp = create_mcp_server(streamable_http_path=path)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
