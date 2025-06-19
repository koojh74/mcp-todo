#!/usr/bin/env python3
"""Test FastMCP Context usage"""

from fastmcp import FastMCP

# Create a test FastMCP instance
mcp = FastMCP("test")

@mcp.tool()
def test_tool(ctx) -> str:
    """Test tool to understand context parameter"""
    print(f"Context type: {type(ctx)}")
    print(f"Context dir: {dir(ctx)}")
    return "success"

if __name__ == "__main__":
    print("FastMCP test complete")