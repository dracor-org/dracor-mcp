from fastmcp import FastMCP
import os

DRACOR_REMOTE_MCP_SERVER = str(os.environ.get("DRACOR_REMOTE_MCP_SERVER", "https://dev.dracor.org/sse"))

proxy = FastMCP.as_proxy(
    DRACOR_REMOTE_MCP_SERVER, 
    name="DraCor Remote MCP Server Proxy"
)

if __name__ == "__main__":
    proxy.run()  # Runs via STDIO for Claude Desktop