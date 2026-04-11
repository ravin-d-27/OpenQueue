import asyncio

from fastmcp import Client


async def main():
    async with Client(
        "http://localhost:8080/mcp",  # You can replace this with your actual MCP server
        auth="your_token",
    ) as client:
        result = await client.call_tool(
            "enqueue_job",
            {
                "queue_name": "sample",
                "payload": {"name": "sample test 1"},
            },
        )
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
