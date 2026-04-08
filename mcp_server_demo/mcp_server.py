from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP("calculator-server")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b


if __name__ == "__main__":
    print("Calculator MCP Server running...")
    mcp.run(transport="stdio")