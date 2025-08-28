from fastmcp import FastMCP

mcp = FastMCP("Sample Streanable MCP")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.prompt
def greet(name: str) -> str:
    """Greet a person by name"""
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")