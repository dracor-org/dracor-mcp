#!/usr/bin/env python3

from typing import Dict, List, Optional, Any, Union
import requests
from mcp.server.fastmcp import FastMCP

# Base API URL for DraCor v1
DRACOR_API_BASE_URL = "https://dev.dracor.org/api/v1"

# Create the FastMCP server instance
mcp = FastMCP("DraCor API v1 (dev)")

# Helper function to make API requests
def api_request(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Make a request to the DraCor API v1."""
    url = f"{DRACOR_API_BASE_URL}/{endpoint}"
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# Resource implementations using decorators
@mcp.resource("info://")
def get_api_info() -> Dict:
    """Get API information and version details."""
    try:
        info = api_request("info")
        return info
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("corpora://")
def get_dts_collections() -> Dict:
    """List of all available corpora (collections of plays) via DTS Collection endpoint"""
    try:
        corpora = api_request("dts/collection")
        return {"corpora": corpora["member"]}
    except Exception as e:
        return {"error": str(e)}

# This does not work with the free version
@mcp.resource("ontology://")
def get_api_ontology() -> Dict:
    """"""
    try:
        data = requests.get("https://raw.githubusercontent.com/ingoboerner/dracor-ontology/refs/heads/main/v1/dracor_api_ontology.ttl")
        return data.text
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("jsonldcontext://")
def get_json_ld_context() -> Dict:
    """"""
    try:
        data = requests.get("https://raw.githubusercontent.com/dracor-org/dracor-ontology/refs/heads/main/json-ld-contexts/dts-extension-context.json")
        return data.text
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run() 

# Will show up as an resource template in the server, but not as a resource, 
# but this does not seem to be supported by
# by Claude Desktop

@mcp.resource("corpora://{corpus_name}")
def get_dts_collection_members(corpus_name: str) -> Dict:
    """Information about a specific corpus via DTS"""
    try:
        corpus = api_request(f"dts/collection?id={corpus_name}")
        return {"corpora": corpus["member"]}
    except Exception as e:
        return {"error": str(e)}

