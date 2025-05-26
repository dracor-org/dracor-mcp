#!/usr/bin/env python3

from typing import Dict, List, Optional, Any, Union
import requests
from requests.auth import HTTPBasicAuth
# from mcp.server.fastmcp import FastMCP
from fastmcp import FastMCP
import os
import csv
from io import StringIO
from urllib.parse import quote
from rdflib import Graph, Namespace, URIRef, RDF, RDFS, OWL
from lxml import etree

# Admin User and Password of the (local) eXist-DB can be supplied as environment variables
DRACOR_EXISTDB_ADMIN = str(os.environ.get("DRACOR_EXISTDB_ADMIN", "admin"))
DRACOR_EXISTDB_PWD = str(os.environ.get("DRACOR_EXISTDB_PWD", ""))

# Base API URL for DraCor v1
# Set the Base URL in the environment variable DRACOR_API_BASE_URL 
DRACOR_API_BASE_URL = str(os.environ.get("DRACOR_API_BASE_URL", "https://staging.dracor.org/api/v1"))

# URL to retrieve the DraCor API Ontology
DRACOR_API_ONTOLOGY_URL = "https://raw.githubusercontent.com/dracor-org/dracor-ontology/refs/heads/main/v1/dracor_api_ontology.ttl"
DRACOR_API_ONTOLOGY_NAMESPACE = Namespace("https://dracor.org/ontology/dracor-api/v1/")

DRACOR_ODD_URL = "https://raw.githubusercontent.com/dracor-org/dracor-schema/refs/heads/main/dracor.odd"

XML_NAMESPACES = {
            'tei': 'http://www.tei-c.org/ns/1.0',
            'xml': 'http://www.w3.org/XML/1998/namespace',
            'eg': 'http://www.tei-c.org/ns/Examples'
        }

DRACOR_RESEARCH_URL = "https://raw.githubusercontent.com/dracor-org/dracor-frontend/refs/heads/main/public/doc/research.md"

DRACOR_RELAXNG_URL = DRACOR_API_BASE_URL.split("/api/")[0] + "/schema.rng"

# Create the FastMCP server instance
mcp = FastMCP("DraCor API v1 (dev)", 
              request_timeout=300)
# timeout need to be set in the inspector 
# see https://github.com/modelcontextprotocol/inspector


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
# TODO: This should be switched to PyDraCor-Core
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

### --------------
###   RESOURCES
### --------------

@mcp.resource("corpora://")
def resource_corpora_via_dts() -> Dict:
    """List of all available corpora (collections of plays) via DTS Collection endpoint"""
    try:
        corpora = api_request("dts/collection")
        return {"corpora": corpora["member"]}
    except Exception as e:
        return {"error": str(e)}

# Will show up as an resource template in the server, but not as a resource, 
# but this does not seem to be supported by
# by Claude Desktop

"""
@mcp.resource("corpora://{corpus_name}")
def get_corpus_via_dts(corpus_name: str) -> Dict:
    #Information about a specific corpus via the DTS endpoint
    try:
        corpus = api_request(f"dts/collection?id={corpus_name}")
        return {"corpus": corpus}
    except Exception as e:
        return {"error": str(e)}
"""

@mcp.resource("registry://")
def resource_corpus_registry() -> Dict:
    """All DraCor Corpora registered in the DraCor Registry"""
    try:
        r = requests.get("https://raw.githubusercontent.com/dracor-org/dracor-registry/refs/heads/main/corpora.json")
        if r.status_code == 200:
            return {"corpora" : r.json()}
        else:
            return {"error" : r.text }
    except Exception as e:
        return {"error" : str(e)}
    

### --------------
###   TOOLS
### --------------

# Regular API

@mcp.tool()
def get_api_info():
    """Get information on the DraCor API
    
    Data is retrieved from the endpoint /info
    """
    try:
        info = api_get()
        return {"info" : info}
    except Exception as e:
        return {"error" : str(e)}

@mcp.tool()
def get_corpora():
    """List all corpora
    
    Data is retrieved from the endpoint /corpora
    """
    try:
        request_url = f"{DRACOR_API_BASE_URL}/corpora?include=metrics"
        r = requests.get(request_url)
        if r.status_code == 200:
            return {"corpora": r.json()}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_corpus(corpus_name: str):
    """Get information on a single corpus

    Data is retrieved from the endpoint /corpora/{corpusname}.
    The tool `get_corpus_content_paged_helper` provides the data on plays included in the corpus in batches.
   
    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
    """
    try:
        corpus = api_request(f"corpora/{corpus_name}")
        return {"corpus": corpus}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_corpus_metadata(corpus_name: str):
    """Get extended metadata of all plays in a corpus
    
    Data is retrieved from the endpoint /corpora/{corpusname}/metadata
    If the data on the plays does not fit into the context use the tool `get_corpus_metadata_paged_helper` instead, 
    which allows for retrieving metadata on the plays in batches.
    

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
    """
    try:
        metadata = api_get(corpusname=corpus_name, method="metadata")
        return {"metadata" : metadata}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_play_metadata(corpus_name: str, 
                      play_name: str):
    """Get metadata and network metrics of a single play
    
    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try:
        play = api_get(corpusname=corpus_name, playname=play_name)
        return {"play" : play}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_play_metrics(corpus_name: str,
                     play_name: str):
    """Get network metrics of a single play
    
    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/metrics

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try: 
        play_metrics = api_get(corpusname=corpus_name, playname=play_name, method="metrics")
        return {"metrics" : play_metrics}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_play_tei(corpus_name: str, play_name:str):
    """Get TEI-XML of a play in a corpus
    
    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/tei

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try:
        request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/tei"
        r = requests.get(request_url)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_play_plaintext(corpus_name:str, play_name:str):
    """Get plaintext of a play in a corpus
    
    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/txt

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try:
        request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/txt"
        r = requests.get(request_url)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_play_characters(corpus_name: str,
                        play_name: str):
    """Get characters of a play
    
    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/characters

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try:
        characters = api_get(corpusname=corpus_name, playname=play_name, method="characters")
        return {"characters" : characters}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_play_network(corpus_name: str,
                         play_name: str):
    """Get the edges of the co-presence network based on a play in a corpus
    
    This tool fetches csv data from the /corpora/{corpusname}/plays/{playname}/networkdata/csv endpoint and 
    serializes it in JSON.

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try:
        request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/networkdata/csv"
        r = requests.get(request_url)
        
        if r.status_code == 200:
            csv_filelike = StringIO(r.text)
            reader = csv.reader(csv_filelike, delimiter=",")
            nodes = []
            edges = []
            # skip the first row:
            next(reader, None) 
            for row in reader:
                if row[0] not in nodes:
                    nodes.append(row[0])
                if row[2] not in nodes:
                    nodes.append(row[2])
                #edges properties: Source,Type,Target,Weight
                item = {}
                item["source"] = row[0]
                item["type"] = row[1].lower()
                item["target"] = row[2]
                item["weight"] = row[3]
                edges.append(item)

        return {"nodes":nodes, "edges": edges}

    except Exception as e:
        return {"error": str(e)}
    
@mcp.tool()
def get_play_character_relations(corpus_name: str, play_name: str):
    """Get character relations in a play
    
    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/relations/csv
    
    This tool returns kinship and other social relationship data, loosely following the encoding scheme proposed in the publication
    Wiedmer / Pagel / Reiter. “Romeo, Freund Des Mercutio: Semi-Automatische Extraktion von Beziehungen zwischen Dramatischen Figuren.”
    DHd2020. Book of Abstracts. Paderborn, 2020: 194–200. https://doi.org/10.5281/zenodo.4621778.

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try:
        request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/relations/csv"
        r = requests.get(request_url)
        
        if r.status_code == 200:
            csv_filelike = StringIO(r.text)
            reader = csv.reader(csv_filelike, delimiter=",")
            relations = []
            # skip the first row:
            next(reader, None) 
            for row in reader:
                # Source,Type,Target,Label
                # odoardo,Directed,emilia,parent_of 
                # claudia,Directed,emilia,parent_of
                item = {}
                item["source"] = row[0]
                item["type"] = row[1].lower()
                item["target"] = row[2]
                item["label"] = row[3]
                relations.append(item)

        return {"relations": relations}

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_spoken_text(corpus_name: str, 
                    play_name: str, 
                    gender = None, 
                    relation = None,
                    role = None):
    """Get spoken text of a play (excluding stage directions)
    
    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/spoken-text

    For a more fine grained access to the spoken text use the tools `get_citable_units_via_dts`in combination with `get_plaintext_of_citable_unit_via_dts`.

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
        gender (str): Filter spoken text by gender, values are `FEMALE`, `MALE`, `UNKNOWN`
        relation (str): Filter spoken text by relation, values are `siblings`, `friends`, `spouses`, `parent_of_active`, `parent_of_passive`, 
            `lover_of_active`, `lover_of_passive`, `related_with_active`, `related_with_passive`, `associated_with_active`, `associated_with_passive`
        role (str): Filter spoken text by role of a character
    """
    try:
        if gender is not None and relation is not None and role is not None:
            request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text?gender={gender}&relation={relation}&role={role}"
        elif gender is None and relation is not None and role is not None:
            request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text?relation={relation}&role={role}"
        elif gender is None and relation is None and role is not None:
            request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text?role={role}"
        elif gender is not None and relation is None and role is not None:
            request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text?gender={gender}&role={role}"
        elif gender is not None and relation is not None and role is None:
            request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text?gender={gender}&relation={relation}"
        elif gender is not None and relation is None and role is None:
            request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text?gender={gender}"
        elif gender is None and relation is not None and role is None:
            request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text?relation={relation}"
        else:
            request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/spoken-text"
        
        r = requests.get(request_url)
        spoken_text = r.text
        return {"text" : spoken_text }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_spoken_text_by_characters(corpus_name: str, 
                    play_name: str):
    """Get spoken text of each character of a play
    
    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/spoken-text-by-character. 
    The items included in the text objects with the key `text` are speech acts.

    For a more fine grained access to the spoken text use the tools `get_citable_units_via_dts`in combination with `get_plaintext_of_citable_unit_via_dts`.

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try:
        texts = api_get(corpusname=corpus_name, playname=play_name, method="spoken-text-by-character")
        return {"spoken-texts" : texts}

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_spoken_text_of_single_character(corpus_name: str, play_name: str, character_id: str):
    """Get spoken text by a single character of a play

    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/spoken-text-by-character but only the text of a 
    single character identified by a character_id is included. The items returned are speech acts.

    For a more fine grained access to the spoken text use the tools `get_citable_units_via_dts`in combination with `get_plaintext_of_citable_unit_via_dts`.

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
        character_id (str): Identifier  of the character, e.g, `marinelli` 
    """
    try:
        all_texts = api_get(corpusname=corpus_name, playname=play_name, method="spoken-text-by-character")
        character_text_data = list(filter(lambda item: item["id"] == character_id, all_texts))
        return {"character-spoken-text": character_text_data[0]["text"]}

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_stage_directions(corpus_name: str, play_name: str):
    """Get the text of all stage directions of a play
    
    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/stage-directions

    For a more fine grained access to the spoken text use the tools `get_citable_units_via_dts`in combination with `get_plaintext_of_citable_unit_via_dts`.

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try:
        stage_directions = api_get(corpusname=corpus_name, playname=play_name, method="stage-directions", parse_json=False)
        return {"stage-directions" : stage_directions}

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_stage_directions_with_speakers(corpus_name: str, play_name: str):
    """Get the text of all stage directions of a play including speakers

    Data is retrieved from the endpoint /corpora/{corpusname}/plays/{playname}/stage-directions-with-speakers
    
    For a more fine grained access to the spoken text use the tools `get_citable_units_via_dts`in combination with `get_plaintext_of_citable_unit_via_dts`.
    
    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    try:
        stage_directions = api_get(corpusname=corpus_name, playname=play_name, method="stage-directions-with-speakers", parse_json=False)
        return {"stage-directions" : stage_directions}

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_plays_with_characters_by_wikidata_id(qid: str):
    """Get plays having a character identified by Wikidata ID

    Data is retrieved from the endpoint /character/{id}

    Args:
        qid (str): Wikidata-ID / Q-Number, e.g. Q131412
    """
    try:
        request_url = f"{DRACOR_API_BASE_URL}/character/{qid}"
        r = requests.get(request_url)
        if r.status_code == 200:
            return {"plays_with_character" : r.json() }
    
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_author_info_from_wikidata(qid:str):
    """Get information about an author from Wikidata
    
    Need to supply the Q-ID/Wikidata Identifier of an author.
    
    Data is retrieved from the endpoint /wikidata/author/{id}

    Args:
        qid (str): Wikidata-ID / Q-Number, e.g. Q34628
    """
    try:
        request_url = f"{DRACOR_API_BASE_URL}/wikidata/author/{qid}"
        r = requests.get(request_url)
        if r.status_code == 200:
            return {"author" : r.json() }
    
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_wikidata_mixnmatch(items_per_page: int = 0, page: int = 0):
    """Wikidata Mix'n'Match DraCor endpoint

    Data is retrieved from the endpoint /wikidata/mixnmatch
    The endpoint returns CSV data that is parsed and returned as JSON 
    It returns id(DraCor ID),name (Main title of a play),q (the Q-Number/Wikidata Identifier if matched to Wikidata). 
    The tool can return batches of items controlled with the parameters items_per_page and page.

    Args:
        items_per_page (int): Number of items to retrieve in a batch. Defaults to 0 (everything is returned at once).
        page (int): Number of page of the results to retrieve in a batch request. Defaults to 0 (everything is returned at once).
    """
    try:
        request_url = f"{DRACOR_API_BASE_URL}/wikidata/mixnmatch"
        r = requests.get(request_url)
        
        data = []
        if r.status_code == 200:
            csv_filelike = StringIO(r.text)
            reader = csv.reader(csv_filelike, delimiter=",")
            # skip the first row:
            next(reader, None) 
            for row in reader:
                item = {}
                item["id"] = row[0]
                item["title"] = row[1].lower()
                if row[2] == "":
                    item["q"] = None
                else:
                    item["q"] = row[2]
                data.append(item)


        # no batch requested if limit and offset are 0 (default)
        if page == 0 and items_per_page == 0:
            result = data
            
            # Pagination object to be returned
            pagination = {}
            pagination["current_page"] = 1
            pagination["items_per_page"] = len(result)
            pagination["total_items"] = len(result)
            pagination["total_pages"] = 1
            pagination["has_next_page"] = False
            pagination["has_previous_page"] = False
           
        else:
            # requested a batch
            total_items = len(data)
            start_index = (page - 1) * items_per_page
            total_pages = (len(data) + items_per_page - 1) // items_per_page
            
            result = data[start_index:start_index + items_per_page]

            pagination = {}
            pagination["current_page"] = page
            pagination["items_per_page"] = items_per_page
            pagination["total_items"] = len(data)
            pagination["total_pages"] = total_pages
            pagination["next_page"] = page < total_pages
            pagination["previous_page"] = page > 1

        return { "pagination": pagination, "data" : data }

    except Exception as e:
        return {"error": str(e)}

# TODO: Tool/Function that filters mix'n'match result by corpus.
@mcp.tool()
def get_links_to_playdata_helper(corpus_name: str, play_name: str):
    """Download Links for Play data
    
    Helper tool to construct links to view play data in different tools or download in different formats. 
    On the one hand the DraCor front end implements several views of a play, including a "Download Tab". 
    The "Tool Tab" provides links to external tools (CLARIN Language Resource Switchboard, Voyant Tools, Gephi lite). 
    This MCP tool provides these links.

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        play_name (str): Identifier (play_name) of a play in a corpus, e.g. `lessing-emilia-galotti`, `gogol-revizor`
    """
    dracor_frontend_base = DRACOR_API_BASE_URL.split("/api/")[0]

    urls = {}
    urls["frontend_network_tab"] = f"{dracor_frontend_base}/{corpus_name}/{play_name}"
    urls["frontend_speech_distribution_tab"] = f"{dracor_frontend_base}/{corpus_name}/{play_name}#speech"
    urls["frontend_fulltext_tab"] = f"{dracor_frontend_base}/{corpus_name}/{play_name}#text"
    urls["frontend_download_tab"] = f"{dracor_frontend_base}/{corpus_name}/{play_name}#downloads"
    urls["frontend_tools_tab"] = f"{dracor_frontend_base}/{corpus_name}/{play_name}#tools"

    # need to encode the url to retrieve the data for the clarin tool
    quoted_play_url = quote(f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/", safe='')

    #CLARIN Language Resource Switchboard
    urls["frontend_tools_tab_to_clarin_language_switchboard_tei_file"] = f"https://switchboard.clarin.eu/#/vlo/{quoted_play_url}tei"
    urls["frontend_tools_tab_to_clarin_language_switchboard_plaintext_file"] = f"https://switchboard.clarin.eu/#/vlo/{quoted_play_url}txt"
    urls["frontend_tools_tab_to_clarin_language_switchboard_spoken-text_file"] = f"https://switchboard.clarin.eu/#/vlo/{quoted_play_url}spoken-text"
    urls["frontend_tools_tab_to_clarin_language_switchboard_stage-directions_file"] = f"https://switchboard.clarin.eu/#/vlo/{quoted_play_url}stage-directions"


    #Voyant Tools
    urls["frontend_tools_tab_to_voyant_tool_tei_file"] = f"https://voyant-tools.org/?input={quoted_play_url}tei"
    urls["frontend_tools_tab_to_voyant_tool_plaintext_file"] = f"https://voyant-tools.org/?input={quoted_play_url}txt"
    urls["frontend_tools_tab_to_voyant_tool_spoken-text_file"] = f"https://voyant-tools.org/?input={quoted_play_url}spoken-text"
    urls["frontend_tools_tab_to_voyant_tool_stage-directions_file"] = f"https://voyant-tools.org/?input={quoted_play_url}stage-directions"

    # Gephi
    urls["frontend_tools_tab_to_gephi"] = f"https://gephi.org/gephi-lite/?file={quoted_play_url}networkdata/gexf"

    # Download Tab Formats
    urls["download_network_data_as_gexf"] = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/networkdata/gexf"
    urls["download_network_data_as_graphml"] = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/networkdata/graphml"
    urls["download_character_relation_data_as_gexf"] = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/relations/gexf"
    urls["download_character_relation_data_as_gexf"] = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/relations/graphml"    

    return {"urls": urls}


# Helper Functions
# These functions support a smoother access of LLMs to the DraCor API, 
# e.g. by providing derived data to make sure it fits into the context of the LLM

@mcp.tool()
def get_minimal_data_of_plays_of_corpus_helper(corpus_name: str,
                               items_per_page: int = 0,
                               page: int = 0):
    """Get a list of plays with main title, identifiers, authors and normalized year in a corpus
    
    This is a more compact format of the data returned by the endpoint /corpora/{corpusname}. 
    It only includes the values of the features play_title play_name, play_id, names of the authors (play_author_shortname) and play_year_normalized.
    This tool allows for requesting batches of items. The default behaviour is to return everything. If limit and offset are explicitly set, batches can be returned.

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        items_per_page (int): Number of items to retrieve in a batch. Defaults to 0 (everything is returned at once).
        page (int): Number of page of the results to retrieve in a batch request. Defaults to 0 (everything is returned at once).
    """
    try:
        corpus = api_get(corpusname=corpus_name)
        result = []
        # no batch requested if limit and offset are 0 (default)
        if page == 0 and items_per_page == 0:
            plays = corpus["plays"]
            
            # Pagination object to be returned
            pagination = {}
            pagination["current_page"] = 1
            pagination["items_per_page"] = len(corpus["plays"])
            pagination["total_plays"] = len(corpus["plays"])
            pagination["total_pages"] = 1
            pagination["has_next_page"] = False
            pagination["has_previous_page"] = False
           
        else:
            # requested a batch
            total_plays = len(corpus["plays"])
            start_index = (page - 1) * items_per_page
            total_pages = (total_plays + items_per_page - 1) // items_per_page
            
            plays = corpus["plays"][start_index:start_index + items_per_page]

            pagination = {}
            pagination["current_page"] = page
            pagination["items_per_page"] = items_per_page
            pagination["total_plays"] = len(corpus["plays"])
            pagination["total_pages"] = total_pages
            pagination["next_page"] = page < total_pages
            pagination["previous_page"] = page > 1

        # plays is either everything or the batch
        for play in plays:

            author_names = []
            for author in play["authors"]:
                author_names.append(author["shortname"]) # feauture play_author_shortname

            item = {}
            item["name"] = play["name"] #feature play_name
            item["id"] = play["id"] #feature play_id
            # item["play_uri"] = DRACOR_API_BASE_URL.split("/api/")[0] + "/id/" + play["id"]
            item["title"] = play["title"] #feature play_title
            item["yearNormalized"] = play["yearNormalized"] #feature play_year_normalized
            item["authors"] = author_names

            result.append(item)

        return {"pagination": pagination, "plays" : result}

    except Exception as e:
        return {"error": str(e)}
    
@mcp.tool()
def get_playnames_in_corpus_helper(corpus_name: str,
                                items_per_page: int = 0,
                                page: int = 0):
    """Get identifiers play_name in a corpus
    
    This is the sortest possible list of plays included in a corpus. It includes only the identifier play_name. 
    It should be possible to at least guess the author from the identifier if it is a slud following the pattern {author-surname}-{title-slug}.
    The tool can return batches of identifiers which can be controlled by setting the parameters items_per_page and page. The default behaviour is to return everything at once.

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        items_per_page (int): Number of items to retrieve in a batch. Defaults to 0 (everything is returned at once).
        page (int): Number of page of the results to retrieve in a batch request. Defaults to 0 (everything is returned at once).
        
    """
    try:
        corpus = api_get(corpusname=corpus_name)
        if items_per_page == 0 and page == 0:
            plays = corpus["plays"]

            # Pagination object to be returned
            pagination = {}
            pagination["current_page"] = 1
            pagination["items_per_page"] = len(corpus["plays"])
            pagination["total_items"] = len(corpus["plays"])
            pagination["total_pages"] = 1
            pagination["has_next_page"] = False
            pagination["has_previous_page"] = False

        else:
            # batches
            total_plays = len(corpus["plays"])
            start_index = (page - 1) * items_per_page
            total_pages = (total_plays + items_per_page - 1) // items_per_page
            
            plays = corpus["plays"][start_index:start_index + items_per_page]

            pagination = {}
            pagination["current_page"] = page
            pagination["items_per_page"] = items_per_page
            pagination["total_items"] = len(corpus["plays"])
            pagination["total_pages"] = total_pages
            pagination["next_page"] = page < total_pages
            pagination["previous_page"] = page > 1

        result = []
        for play in plays:
            result.append(play["name"])
        return {"pagination": pagination ,"play_names" : result }
    
    except Exception as e:
        return {"error": str(e)}
    
@mcp.tool()
def get_corpus_metadata_paged_helper(corpus_name:str, 
                                    items_per_page: int = 50,
                                    page: int = 1 ):
    """Get metadata on all plays in a corpus in batches

    Data is retrieved from the endpoint /corpora/{corpusname}/metadata, but in batches.
    This normally times out; that is a problem of the API 
    
    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        items_per_page (int): Number of play metadata to retrieve in a batch. Defaults to 50.
        page (int): Number of page of the results to retrieve in a batch request. Defaults to 1 – the first 50 plays.
    """
    try:
        metadata = api_get(corpusname=corpus_name, method="metadata")

        total_items = len(metadata)
        start_index = (page - 1) * items_per_page
        total_pages = (total_items + items_per_page - 1) // items_per_page
            
        items = metadata[start_index:start_index + items_per_page]

        pagination = {}
        pagination["current_page"] = page
        pagination["items_per_page"] = items_per_page
        pagination["total_items"] = len(corpus["plays"])
        pagination["total_pages"] = total_pages
        pagination["next_page"] = page < total_pages
        pagination["previous_page"] = page > 1

        return {"pagination": pagination ,"plays" : items }
    
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_corpus_contents_paged_helper(corpus_name:str, 
                                    items_per_page: int = 25,
                                    page: int = 1 ):
    """Get corpus contents in batches

    Data is retrieved from the endpoint /corpora/{corpusname}. It does not include the metadata on the corpus, only the plays included.
    
    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        items_per_page (int): Number of play metadata to retrieve in a batch. Defaults to 25.
        page (int): Number of page of the results to retrieve in a batch request. Defaults to 1 – the first 25 plays.
    """
    try:
        corpus = api_get(corpusname=corpus_name)

        total_items = len(corpus["plays"])
        start_index = (page - 1) * items_per_page
        total_pages = (total_items + items_per_page - 1) // items_per_page
            
        plays_to_return = corpus["plays"][start_index:start_index + items_per_page]

        pagination = {}
        pagination["current_page"] = page
        pagination["items_per_page"] = items_per_page
        pagination["total_items"] = len(corpus["plays"])
        pagination["total_pages"] = total_pages
        pagination["next_page"] = page < total_pages
        pagination["previous_page"] = page > 1

        return {"pagination": pagination ,"plays" : plays_to_return }
    
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_plays_in_corpus_by_author_helper(corpus_name: str, author_name:str):
    """Filter plays in a corpus by author

    Data is retrieved from the endpoint /corpora/{corpusname}. The list of included plays is filtered.
    The tool checks if the author_name supplied is contained in any of the included authors name field.

    
    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        author_name (str): Name of an author, e.g. "Goethe", "Shakespeare"
    """

    try:
        corpus = api_get(corpusname=corpus_name)
        plays_by_author = []

        for item in corpus["plays"]:
            
            for author in item["authors"]:
                if author_name in author["name"]:
                    plays_by_author.append(item)
                    break
                    
        return {"plays" : plays_by_author}

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_plays_in_corpus_by_title_helper(corpus_name: str, title: str):
    """Filter plays in a corpus by (main) title

    Data is retrieved from the endpoint /corpora/{corpusname}. The list of included plays is filtered.
    The tool checks if the title supplied is contained in field with the key "title" (feature play_title).

    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        author_name (str): Main title of play, e.g. `Faust`, `Tempest`
    """

    try:
        corpus = api_get(corpusname=corpus_name)
        plays = list(filter(lambda item: title.lower() in item["title"].lower(), corpus["plays"]))
        return {"plays" : plays}

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_plays_in_corpus_by_year_normalized(corpus_name: str, year_start: int, year_end: int):
    """Get plays in a corpus by year normalized
    
    Data is retrieved from the endpoint /corpora/{corpusname}. The list of included plays is filtered.
    The tool checks if the value of yearNormalized is in the range of year_start and year_end.
    
    Args:
        corpus_name (str): Identifier of a corpus, e.g. `ger`, `rus`, `als`
        year_start (int): Start year
        year_end (ind): End year
    """
    try:
        corpus = api_get(corpusname=corpus_name)
        plays = list(filter(lambda item: year_start <= item["yearNormalized"] <= year_end, corpus["plays"]))
        return {"plays" : plays}

    except Exception as e:
        return {"error": str(e)}

# Look up play titles, authors, identifiers, normalized year – should be relatively sparse data to possibly fit into the whole context

# Improve explainability: parse ontology, provide information on a single feature
# Parse OpenAPI, provide information on an endpoint


# DTS Endpoints
@mcp.tool()
def dts_entrypoint():
    """Get DTS Entrypoint
    
    Retrieve information about the DraCor DTS implementation. The data includes the version of the DTS Specification implemented and
    provides URI Templates  as defined in RFC 6570 to the other DTS endpoint (Collection, Navigation, Document).
    """
    try:
        r = requests.get(f"{DRACOR_API_BASE_URL}/dts")
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        return {"error": str(e)}
    
# TODO: DTS Collection endpoint generic tool
# TODO: DTS Navigation endpoint generic tool
# TODO: DTS Documentation endpoint generic tool

# DTS specific tools

# A tool for Claude to get a single corpus (because he can't work with the Resource template)
@mcp.tool()
def get_corpus_via_dts(corpus_name: str):
    """Get Information on a Corpus via the DTS API
    
    This tool uses the DTS (Distributed Text Services) Collection endpoint /dts/collection to retrieve the data.

    Args:
        corpus_name (str): Identifier/URI of the corpus, e.g. `https://staging.dracor.org/id/ger` or `ger`
    """
    try:
        corpus = api_request(f"dts/collection?id={corpus_name}")
        return {"corpus": corpus}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_play_via_dts(play_uri: str):
    """Get Information on a Play via the DTS API
    
    This tool uses the DTS (Distributed Text Services) Collection endpoint /dts/collection to retrieve the data.

    Args:
        play_uri (str): Identifier/URI of the play, e.g. `https://staging.dracor.org/id/ger000088`
    """
    try:
        play = api_request(f"dts/collection?id={play_uri}")
        return {"play": play}
    except Exception as e:
        return {"error": str(e)}
    
@mcp.tool()
def get_citable_units_via_dts(
    play_uri: str,
    ref:str = None,
    down:str = "-1"):
    """Get Information on a Citable Units via the DTS API

    This tool allows to retrieve structural information of a play based on the DTS (Distributed Text Services) Navigation endpoint /dts/navigation. 
    To get the citable units of a single segment use the parameter "ref" 
    with the segment identifier, e.g. `div[1]/div[1]` 
    to get the first scene of the first act.
    To retrieve all citable units set the parameter "down" to `-1`
    
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
def get_plaintext_of_citable_unit_via_dts(play_uri: str, ref:str):
    """Get the text of a Citable Unit

    This tool uses the DTS (Distributed Text Services) Document endpoint /dts/document to retrieve the data.
    
    Args:
        play_uri (str): Identifier/URI of the play, e.g. `https://staging.dracor.org/id/ger000088`
        ref (str): Fragment identifier, e.g of the first scene of the second act `body/div[2]/div[1]`
    """
    try:
        response = requests.get(f"{DRACOR_API_BASE_URL}/dts/document?resource={play_uri}&ref={ref}&mediaType=text/plain")
        return {"text": response.text}
    except Exception as e:
        return {"error": str(e)}
    
# Documentation Tools

def parse_property_info_helper(ontology, prop, NS):
    """
    Parse information about a specific property from the graph.
    
    Args:
        ontology (Graph): RDF graph containing the DraCor API ontolgoy
        prop (URIRef): URI reference to the property
        NS (Namespace): DraCor API Namespace namespace
        
    Returns:
        dict: Dictionary containing the property's information
    """
    prop_info = {
        "uri": prop,
        "name": prop.split("/")[-1]
    }
    
    # Get rdfs:domain
    domains = list(ontology.objects(prop, RDFS.domain))
    prop_info["domain"] = [str(d) for d in domains] if domains else None
    
    # Get rdfs:range
    ranges = list(ontology.objects(prop, RDFS.range))
    prop_info["range"] = [str(r) for r in ranges] if ranges else None
    
    # Get rdfs:label
    labels = list(ontology.objects(prop, RDFS.label))
    prop_info["label"] = str(labels[0]) if labels else None
    
    # Get rdfs:comment
    comments = list(ontology.objects(prop, RDFS.comment))
    prop_info["comment"] = str(comments[0]) if comments else None
    
    # Get DraCor-specific properties
    feature_ids = list(ontology.objects(prop, NS.feature_id))
    prop_info["feature_id"] = str(feature_ids[0]) if feature_ids else None
    
    feature_names = list(ontology.objects(prop, NS.feature_name))
    prop_info["feature_name"] = str(feature_names[0]) if feature_names else None
    
    extractors_module = list(ontology.objects(prop, NS.extractor_in_api_module))
    prop_info["extractor_in_api_module"] = str(extractors_module[0]) if extractors_module else None
    
    extractors_function = list(ontology.objects(prop, NS.extractor_in_api_function))
    prop_info["extractor_in_api_function"] = str(extractors_function[0]) if extractors_function else None
    
    code_refs = list(ontology.objects(prop, NS.code_ref))
    prop_info["code_ref"] = [str(c) for c in code_refs] if code_refs else None
    
    xpaths = list(ontology.objects(prop, NS.xpath))
    prop_info["xpath"] = str(xpaths[0]) if xpaths else None
    
    operation_ids = list(ontology.objects(prop, NS.operation_id))
    prop_info["operation_id"] = [str(o) for o in operation_ids] if operation_ids else None
    
    field_keys = list(ontology.objects(prop, NS.field_key))
    prop_info["field_key"] = [str(k) for k in field_keys] if field_keys else None
    
    return prop_info

@mcp.tool()
def get_api_feature_list():
    """Get a list of API features
    
    Parses the DraCor API Ontolgy and retuns a list of supported API features – types of data included in the API responses
    
    """
    try:
        ontology = Graph()
        ontology.parse(DRACOR_API_ONTOLOGY_URL)

        # Define namespaces
        DRACOR = DRACOR_API_ONTOLOGY_NAMESPACE
    
        # Find all properties in the graph
        properties = []
    
        # Look for owl:DatatypeProperty and rdf:Property
        for prop in ontology.subjects(RDF.type, OWL.DatatypeProperty):
            if (prop, RDF.type, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#Property")) in ontology:
                properties.append(parse_property_info_helper(ontology, prop, DRACOR))
    
        # Also search for any that are just rdf:Property but not owl:DatatypeProperty
        for prop in ontology.subjects(RDF.type, RDF.Property):
            if prop not in [p["uri"] for p in properties]:
                properties.append(parse_property_info_helper(ontology, prop, DRACOR))

        result = []
        # Build a reduced list
        for prop in properties:
            
            # only include properties that have a feature name (might be problematic, but will see)
            if prop["feature_name"]:
                item = {}
                item["feature_name"] = prop["feature_name"]
                item["uri"] = prop["uri"]
                item["comment"] = prop["comment"]
                result.append(item)
                

        return {"features" : result}
        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_api_feature(feature_name:str):
    """Get description of an API feature
    
    Parses the DraCor API Ontolgy and retuns the data on a single API feature
    
    Args:
        feature_name (str): Name of the feature, e.g. play_name, corpus_num_of_characters_male
    """
    try:
        ontology = Graph()
        ontology.parse(DRACOR_API_ONTOLOGY_URL)
        prop = URIRef(DRACOR_API_ONTOLOGY_NAMESPACE + feature_name)
        prop_data = parse_property_info_helper(ontology, prop, DRACOR_API_ONTOLOGY_NAMESPACE)
        return prop_data

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_openapi_specification():
    """Get the OpenAPI Specification of the DraCor API

    Returns the YAML file of the OpenAPI Specification
    
    """
    try:
        r = requests.get(f"{DRACOR_API_BASE_URL}/info")
        info = r.json()
        open_api_url = info["openapi"]
        
        r = requests.get(open_api_url)
        return r.text

    except Exception as e:
        return {"error": str(e)}


def parse_odd_helper():
    """Helper function to parse the ODD from the GitHub Repo"""
    # Use a permissive parser to handle potential issues
    parser = etree.XMLParser(remove_blank_text=True, recover=True)
        
    # Fetch and parse the XML
    r = requests.get(DRACOR_ODD_URL)
    root = etree.fromstring(r.content, parser)
    
    return root
    
@mcp.tool()
def get_table_of_contents_from_odd():
    """
    Get a Table of Contents of the DraCor ODD including the Encoding Guidelines
        
    Returns:
        dict: JSON-serializable dictionary representing the structure of the ODD
    """
    try:
        # Define XML namespaces
        namespaces = XML_NAMESPACES
        
        
        root = parse_odd_helper()
        
        # Process divs recursively to build the TOC
        def process_div(div):
            # Get the div's xml:id
            div_id = div.get("{%s}id" % namespaces['xml'], '')
            
            if not div_id:
                return None
            
            # Get the div's heading
            head = div.find("./tei:head", namespaces)
            
            title = "Untitled Section"
            if head is not None:
                # Extract text content - fixed xpath usage
                all_text = ""
                for text in head.xpath(".//text()"):
                    all_text += text
                title = all_text.strip()
                
                if not title:
                    title = "Untitled Section"
            
            # Create entry for this div
            result = {
                "title": title,
                "children": {}
            }
            
            # Process child divs
            for child_div in div.findall("./tei:div", namespaces):
                child_entry = process_div(child_div)
                if child_entry:
                    child_id = child_div.get("{%s}id" % namespaces['xml'])
                    if child_id:  # Make sure child_id exists
                        result["children"][child_id] = child_entry
            
            return result
        
        # Start processing from body
        toc = {}
        body = root.find(".//tei:body", namespaces)
        
        if body is not None:
            # Get all top-level divs in body
            for div in body.findall("./tei:div", namespaces):
                # Skip example elements
                if not any(parent.tag.endswith('egXML') for parent in div.iterancestors()):
                    entry = process_div(div)
                    if entry:
                        div_id = div.get("{%s}id" % namespaces['xml'])
                        if div_id:
                            toc[div_id] = entry
        
        return toc
        
    except etree.XMLSyntaxError as e:
        return {"error": f"XML parsing error: {str(e)}"}
    except Exception as e:
        return {"error": f"Error processing XML: {str(e)}"}

@mcp.tool()
def get_odd_section(section_id: str):
    """Get a section of the ODD

    Use the tool get_table_of_contents_from_odd to get the IDs of section to retrieve.
    
    Args:
        section_id (str): Identifier (xml:id) of the section
    """
    try:
        root = parse_odd_helper()
        element = root.xpath(f"//*[@xml:id='{section_id}']", namespaces=XML_NAMESPACES)
        return etree.tostring(element[0], encoding='unicode', pretty_print=True)
        
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_tei_element_documentation_from_odd(element_name:str):
    """Get documentation of an element from the DraCor ODD
    
    Args:
        element_name (str): Name of a TEI element, e.g. listPerson
    """
    try:
        root = parse_odd_helper()
        element = root.xpath(f"//tei:elementSpec[@ident='{element_name}']", namespaces=XML_NAMESPACES)
        return etree.tostring(element[0], encoding='unicode', pretty_print=True)        
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_schematron_rule_to_check_api_feature(feature_name:str):
    """Get Schematron rule to check for an DraCor API feature

    In the DraCor schema there are embedded Schematron rules that allow to check if an ecoded TEI-File can be used by the API to retrieve
    a data value.

    Args:
        feature_name (str): ID of a DraCor API feature, e.g. play_id
    """ 
    try:
        root = parse_odd_helper()
        element = root.xpath(f"//tei:constraintSpec[@ident='{feature_name}'][@type='api_feature_check']", namespaces=XML_NAMESPACES)
        return etree.tostring(element[0], encoding='unicode', pretty_print=True)      
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_dracor_based_research():
    """Get Research based on DraCor
    
    This tool makes the research listed at https://dracor.org/doc/research available for the LLM to process. 
    It reads the YAML file in the dracor-frontend GitHub Repo
    """
    try:
        r = requests.get(DRACOR_RESEARCH_URL)
        return r.text
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_readme_form_dracor_api_github_repo():
    """Get the DraCor API Readme
    
    The tool makes available the Readme file in the DraCor API Code repository (https://github.com/dracor-org/dracor-api) on GitHub. 
    It includes information on how to run a local DraCor instance using Docker. 
    """
    try:
        request_url = "https://raw.githubusercontent.com/dracor-org/dracor-api/refs/heads/main/README.md"
        r = requests.get(request_url)
        return r.text
    except Exception as e:
        return {"error": str(e)}


# Editing Support

def get_relaxng_schema_helper(schema_url: str = DRACOR_RELAXNG_URL):
    """Get DraCor RelaxNG Schema
    
    Helper function to fetch and parse the DraCor RelaxNG Schema
    """
    
    try:
        r = requests.get(schema_url)
        relax_ng_doc = etree.fromstring(r.content)
        # build the schema
        schema = etree.RelaxNG(relax_ng_doc)
        return schema
    except Exception as e:
        return {"error" : str(e)}    

@mcp.tool()
def validate_xml_file(file_name: str, file_content: str, schema_url:str = DRACOR_RELAXNG_URL):
    """Validate XML File

    Validate the content of a XML file against the DraCor schema.

    Args:
        file_name (str): Name of the file
        file_content (str): Content of the attached XML file
        schema_url (str): URL of the DraCor Schema. 
            Setting is optional, don't do it if not explicitly stated in the prompt.
    """
    try:
        doc = etree.fromstring(file_content.encode('utf-8'))
        schema = get_relaxng_schema_helper(schema_url = schema_url)
        valid = schema.validate(doc)
        if valid:
            return {"valid": valid,
                    "comment": f"The XML validates against the DraCor RelaxNG schema from {schema_url}."}
        else:
            return {"valid": valid,
                    "comment": f"The XML does not validate against the DraCor RelaxNG schema from {schema_url}. See error log",
                    "error_log": schema.error_log}
    except Exception as e:
        return {"error": str(e)}

# Admin functions (for local instances)

@mcp.tool()
def add_corpus(corpus_metadata: dict):
    """Add a corpus
    
    Add a corpus to a (local) DraCor instance. It is necessary to have write access to the underlying 
    eXist-DB database. Admin and password need to be set as environment variables DRACOR_EXISTDB_ADMIN and DRACOR_EXISTDB_PWD in the MCP server. 
    
    Example of the metadata: {"name": "test", "title": "Test Drama Corpus", "repository": "https://github.com/dracor-org/testdracor"}
        

    Args:
        corpus_metadata (dict): Metadata of the corpus, e.g. {"name": "test", "title": "Test Drama Corpus", "repository": "https://github.com/dracor-org/testdracor"}
    """
    try:
        credentials = HTTPBasicAuth(DRACOR_EXISTDB_ADMIN, DRACOR_EXISTDB_PWD)
        request_url = f"{DRACOR_API_BASE_URL}/corpora"
        r = requests.post(request_url, json=corpus_metadata, auth=credentials)
        if r.status_code == 200 or r.status_code == 201:
            return {"status" : "Success",
                    "status_code" : r.status_code,
                    "api_response" : r.json()}
        elif r.status_code == 409:
            return {"status" : "Failed",
                    "status_code" : r.status_code,
                    "api_response" : r.json(),
                    "comment" : "Corpus already exists!"}
        else: 
            return {
                "status" : "Failed",
                "status_code" : r.status_code}
    except Exception as e:
        return {"error": str(e)}
    
@mcp.tool()
def load_corpus_from_repository(corpus_name: str):
    """Load corpus from GitHub Repository
    
    Load plays from a GitHub repository into a (local) DraCor instance.
    It is necessary to have write access to the underlying 
    eXist-DB database. Admin and password need to be set as environment variables DRACOR_EXISTDB_ADMIN and DRACOR_EXISTDB_PWD in the MCP server.
    
    Args:
        corpus_name (str): Identifier corpus_name of the corpus to load data from GitHub into
    """
    try:
        credentials = HTTPBasicAuth(DRACOR_EXISTDB_ADMIN, DRACOR_EXISTDB_PWD)
        request_url = request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}"
        payload = {"load" : True}
        r = requests.post(request_url, json=payload, auth=credentials)
        if r.status_code == 202:
            return {"status" : "Success",
                    "status_code" : r.status_code,
                    "api_response" : r.json(),
                    "comment": "Corpus update has been scheduled. It may take some time until the data has been loaded."}
        elif r.status_code == 404:
            return {"status" : "Failed",
                    "status_code" : r.status_code,
                    "api_response" : r.json(),
                    "comment" : f"Corpus with the identifier {corpus_name} does not exist!"}
        elif r.status_code == 409:
            return {"status" : "Failed",
                    "status_code" : r.status_code,
                    "api_response" : r.json(),
                    "comment" : f"Corpus update could not be scheduled. This is the response when another update has not yet finished."}
        else:
            return {
                "status" : "Failed",
                "status_code" : r.status_code}

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_play_to_corpus(corpus_name:str, play_name: str, tei: str):
    """Add play
    
    Add the TEI-file of a play to a corpus in a (local) DraCor instance.
    It is necessary to have write access to the underlying eXist-DB database. Admin and password need to be set as environment variables DRACOR_EXISTDB_ADMIN and DRACOR_EXISTDB_PWD in the MCP server. 

    Args:
        corpus_name (str): Identifier of a corpus
        play_name (str): Identifier (play_name) of a play in a corpus
        tei (str): TEI-XML encoded play
    """
    try:
        credentials = HTTPBasicAuth(DRACOR_EXISTDB_ADMIN, DRACOR_EXISTDB_PWD)
        request_url = request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/tei"
        headers = {"Content-Type": "application/xml"}
        
        # should TEI file be parsed and validated?
        
        r = requests.put(request_url, data=tei, headers=headers, auth=credentials)
        if r.status_code == 200:
            return {"status" : "Success",
                    "status_code" : r.status_code,
                    "comment" : f"Play {play_name} has been added to corpus {corpus_name}."}
        elif r.status_code == 400:
            return {"status" : "Failed",
                    "status_code" : r.status_code,
                    "comment" : f"The request body is not a valid TEI document or the playname is invalid."}
        elif r.status_code == 404:
            return {"status" : "Failed",
                    "status_code" : r.status_code,
                    "comment" : f"Corpus {corpus_name} does not exist."}
        else:
            return {
                "status" : "Failed",
                "status_code" : r.status_code}

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def remove_play_from_corpus(corpus_name:str, play_name: str):
    """Remove play from corpus

    Remove a play from a corpus in a (local) DraCor instance.
    It is necessary to have write access to the underlying 
    eXist-DB database. Admin and password need to be set as environment variables DRACOR_EXISTDB_ADMIN and DRACOR_EXISTDB_PWD in the MCP server. 

    Args:
        corpus_name (str): Identifier of a corpus
        play_name (str): Identifier (play_name) of a play in a corpus
    """
    try:
        credentials = HTTPBasicAuth(DRACOR_EXISTDB_ADMIN, DRACOR_EXISTDB_PWD)
        request_url = request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}"
        r = requests.delete(request_url, auth=credentials)
        if r.status_code == 200:
            return {"status" : "Success",
                    "status_code" : r.status_code,
                    "api_response" : r.json(),
                    "comment" : f"Play {play_name} has been removed from corpus {corpus_name}."}
        elif r.status_code == 404:
            return {"status" : "Failed",
                    "status_code" : r.status_code,
                    "api_response" : r.json(),
                    "comment" : f"Play and/or corpus do not exist."}
        else:
            return {
                "status" : "Failed",
                "status_code" : r.status_code}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def remove_corpus(corpus_name: str):
    """Remove corpus
    
    Remove a corpus from a (local) DraCor instance. It is necessary to have write access to the underlying 
    eXist-DB database. Admin and password need to be set as environment variables DRACOR_EXISTDB_ADMIN and DRACOR_EXISTDB_PWD in the MCP server. 
    
    Args:
        corpus_name (str): Identifier corpus_name of the corpus to remove

    """
    try:
        credentials = HTTPBasicAuth(DRACOR_EXISTDB_ADMIN, DRACOR_EXISTDB_PWD)
        request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}"
        r = requests.delete(request_url, auth=credentials)
        if r.status_code == 200:
            return {"status" : "Success",
                    "status_code" : r.status_code,
                    "api_response" : r.json()}
        elif r.status_code == 404:
            return {"status" : "Failed",
                    "status_code" : r.status_code,
                    "api_response" : r.json(),
                    "comment" : f"Corpus with the identifier {corpus_name} does not exist!"}
        else: 
            return {
                "status" : "Failed",
                "status_code" : r.status_code}
            
    except Exception as e:
        return {"error": str(e)}




### --------------
###   PROMPTS
### --------------


# This runs the server.
# Is ignored, when run with fastmcp dracor_mcp.py or fastmcp dev dracor_mcp.py
# but becomes relevant when run in Docker container
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=9000
    )