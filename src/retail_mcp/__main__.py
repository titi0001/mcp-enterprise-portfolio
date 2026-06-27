"""CLI entry point for HTTP or STDIO transport."""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Retail Enterprise MCP server")
    parser.add_argument("--transport", choices=("http", "stdio"), default="http")
    args = parser.parse_args()
    if args.transport == "stdio":
        from retail_mcp.server import mcp

        mcp.run(transport="stdio")
        return

    from retail_mcp.server import settings

    uvicorn.run(
        "retail_mcp.api:app",
        host=settings.host,
        port=settings.port,
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
    )


if __name__ == "__main__":
    main()
