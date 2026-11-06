#!/usr/bin/env python3
"""Smoke test a running DraCor MCP server.

Usage: python test/smoke.py [URL]   (default: http://localhost:8000/mcp)

Waits for the server, then checks that the MCP handshake works and that the
expected tools and resources are registered. Does not call any tools, so it
does not depend on the DraCor API being reachable.
"""

import asyncio
import sys

from fastmcp import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"

EXPECTED_TOOLS = {"get_api_info", "get_corpora", "get_play_metadata",
                  "get_play_network", "get_citable_units_via_dts"}
EXPECTED_RESOURCES = {"corpora://", "registry://"}


async def main():
    for attempt in range(30):
        try:
            async with Client(URL) as client:
                tools = {t.name for t in await client.list_tools()}
                resources = {str(r.uri) for r in await client.list_resources()}
                break
        except Exception as e:
            last_error = e
            await asyncio.sleep(1)
    else:
        sys.exit(f"Could not connect to {URL}: {last_error}")

    print(f"{len(tools)} tools, {len(resources)} resources")
    missing = (EXPECTED_TOOLS - tools) | (EXPECTED_RESOURCES - resources)
    if missing:
        sys.exit(f"Missing: {sorted(missing)}")
    print("OK")


asyncio.run(main())
