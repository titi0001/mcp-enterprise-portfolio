"""Non-destructive Streamable HTTP protocol smoke test."""

import argparse
import asyncio
import os
import sys

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import AnyUrl


async def smoke_test() -> None:
    url = os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")
    api_key = os.getenv("MCP_API_KEY", "dev-admin-key")
    async with httpx.AsyncClient(headers={"X-API-Key": api_key}) as http_client:
        async with streamable_http_client(url, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                print("Initializing MCP session...", flush=True)
                await session.initialize()
                print("Listing MCP capabilities...", flush=True)
                tools = await session.list_tools()
                templates = await session.list_resource_templates()
                prompts = await session.list_prompts()
                print("Reading inventory resource...", flush=True)
                inventory = await session.read_resource(AnyUrl("retail://inventory/SKU-RED-01"))
                assert len(tools.tools) == 3
                assert len(templates.resourceTemplates) == 3
                assert len(prompts.prompts) == 1
                assert inventory.contents
                print("MCP smoke test passed: 3 tools, 3 resources, 1 prompt")


async def wait_until_live(url: str, attempts: int = 50) -> None:
    health_url = url.removesuffix("/mcp") + "/health/live"
    async with httpx.AsyncClient() as client:
        for _ in range(attempts):
            try:
                response = await client.get(health_url, timeout=0.5)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.1)
    raise RuntimeError("MCP server did not become live")


async def run_with_server() -> None:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "retail_mcp",
        "--transport",
        "http",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        await wait_until_live(os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp"))
        await asyncio.wait_for(smoke_test(), timeout=15)
    finally:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            process.kill()
            await process.wait()
        if process.returncode not in (0, -15):
            output = await process.stdout.read() if process.stdout else b""
            print(output.decode("utf-8", errors="replace"), file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start-server",
        action="store_true",
        help="Start and stop a local server around the protocol checks",
    )
    arguments = parser.parse_args()
    asyncio.run(run_with_server() if arguments.start_server else smoke_test())
