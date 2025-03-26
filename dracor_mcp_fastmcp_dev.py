#!/usr/bin/env python3

from typing import Dict, List, Optional, Any, Union
import requests
from mcp.server.fastmcp import FastMCP
import os

# Base API URL for DraCor v1
# Set the Base URL in the environment variable DRACOR_API_BASE_URL 
DRACOR_API_BASE_URL = str(os.environ.get("DRACOR_API_BASE_URL", "https://staging.dracor.org/api/v1"))

# Create the FastMCP server instance
mcp = FastMCP("DraCor API v1 (dev)")

# Helper function to make API requests
def api_request(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Make a request to the DraCor API v1."""
    url = f"{DRACOR_API_BASE_URL}/{endpoint}"
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

# Additional helper function to make DraCor API requests
# We can not use PyDraCor at the moment because the methods to retrieve data via th DTS endpoint
# have not been implemented in PyDraCor yet and it is up do discussion, if integrating them makes much sense. 
# We use a generic function with the Python package 'requests' to connect to the API
def api_get(corpusname:str = None, 
        playname:str = None, 
        apibase:str = DRACOR_API_BASE_URL,
        method:str = None,
        parse_json:bool = True):
    """
    Generic Method to retrieve data from the DraCor API
    """
    
    # Remove tailing slash in apibase if not set, otherwhise concatinating url parameters would not work as expected
    
    if apibase is not None:
        if apibase.endswith("/"):
            apibase = apibase[:-1]
            

    # Both parameters corpusname an playname are supplied
    if corpusname is not None and playname is not None :
        # used for /api/corpora/{corpusname}/plays/{playname}/
        if method is not None:
            request_url = f"{apibase}/corpora/{corpusname}/plays/{playname}/{method}"
        else:
            request_url = f"{apibase}/corpora/{corpusname}/plays/{playname}"

    # no playname set, use the .../corpora/{method} routes 
    elif corpusname is not None and playname is None:
        if method is not None:
            request_url = f"{apibase}/corpora/{corpusname}/{method}"
        else:
            request_url = f"{apibase}/corpora/{corpusname}"
    
    # only a method is set
    elif method is not None and corpusname is None and playname is None:
            request_url = f"{apibase}/{method}"
    else: 
        #nothing is set, return information on the API
        request_url = f"{apibase}/info"
    
    #send the response
    r = requests.get(request_url)
    if r.status_code == 200:
        # successful request, decide if response need to be parsed
        if parse_json is True:
            return r.json()
        else:
            return r.text
    else:
        raise Exception(f"Request was not successful. Server returned status code: {str(r.status_code)}")


# Resource implementations using decorators
@mcp.resource("info://")
def get_api_info() -> Dict:
    """Get API information and version details."""
    try:
        info = api_get(method="info")
        return info
    except Exception as e:
        return {"error": str(e)}

@mcp.resource("corpora://")
def get_corpora_via_dts() -> Dict:
    """List of all available corpora (collections of plays) via DTS Collection endpoint"""
    try:
        corpora = api_request("dts/collection")
        return {"corpora": corpora["member"]}
    except Exception as e:
        return {"error": str(e)}

# Will show up as an resource template in the server, but not as a resource, 
# but this does not seem to be supported by
# by Claude Desktop

@mcp.resource("corpora://{corpus_name}")
def get_corpus_via_dts(corpus_name: str) -> Dict:
    """Information about a specific corpus via the DTS endpoint"""
    try:
        corpus = api_request(f"dts/collection?id={corpus_name}")
        return {"corpus": corpus}
    except Exception as e:
        return {"error": str(e)}

# A tool for Claude to get a single corpus (because he can't work with the Resource template)
@mcp.tool()
def get_corpus_via_dts(corpus_name: str):
    """Get Information on a Corpus via the DTS API"""
    try:
        corpus = api_request(f"dts/collection?id={corpus_name}")
        return {"corpus": corpus}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_play_via_dts(play_uri: str):
    """Get Information on a Play via the DTS API"""
    try:
        play = api_request(f"dts/collection?id={play_uri}")
        return {"play": play}
    except Exception as e:
        return {"error": str(e)}
    
@mcp.tool()
def get_citeable_units_via_dts(
    play_uri: str,
    ref:str = None,
    down:str = "-1"):
    """Get Information on a Citeable Units via the DTS API

    This tool allows to retrieve structural information of a play. 
    To get the citeable units of a single segment use the parameter "ref" 
    with the segment identifier, e.g. `div[1]/div[1]` 
    to get the first scene of the first act.
    To retrieve all citeable units set the parameter "down" to `-1`
    
    Args:
        play_uri (str): Identifier/URI of the play, e.g. `https://staging.dracor.org/id/ger000088`
        ref (str): Fragment identifier, e.g of the first scene of the second act `body/div[2]/div[1]`
        down (str): depth to which to retrieve nested citeable units, e.g. one level deep `1`, all `-1`. 

    """
    try:
        
        if ref and down:
            response = api_request(f"dts/navigation?resource={play_uri}&ref={ref}&down={down}")
        elif ref and not down:
            response = api_request(f"dts/navigation?resource={play_uri}&ref={ref}&down=-1")
        else:
            response = api_request(f"dts/navigation?resource={play_uri}&down=-1")
        
        return {"citeable_units": response["member"]}
    except Exception as e:
        return {"error": str(e)}
    
@mcp.tool()
def get_plaintext_of_citeable_unit_via_dts(play_uri: str, ref:str):
    """Get the Text of a Citeable Unit
    
    Args:
        play_uri (str): Identifier/URI of the play, e.g. `https://staging.dracor.org/id/ger000088`
        ref (str): Fragment identifier, e.g of the first scene of the second act `body/div[2]/div[1]`
    """
    try:
        response = requests.get(f"{DRACOR_API_BASE_URL}/dts/document?resource={play_uri}&ref={ref}&mediaType=text/plain")
        return {"text": response.text}
    except Exception as e:
        return {"error": str(e)}