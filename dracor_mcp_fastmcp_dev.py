#!/usr/bin/env python3

from typing import Dict, List, Optional, Any, Union
import requests
from mcp.server.fastmcp import FastMCP
import os
import csv
from io import StringIO

# Base API URL for DraCor v1
# Set the Base URL in the environment variable DRACOR_API_BASE_URL 
DRACOR_API_BASE_URL = str(os.environ.get("DRACOR_API_BASE_URL", "https://staging.dracor.org/api/v1"))

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
    try:
        request_url = f"{DRACOR_API_BASE_URL}/corpora/{corpus_name}/plays/{play_name}/tei"
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
        id (str): Wikidata-ID / Q-Number, e.g. Q131412
    """
    try:
        request_url = f"{DRACOR_API_BASE_URL}/character/{qid}"
        r = requests.get(request_url)
        if r.status_code == 200:
            return {"plays_with_character" : r.json() }
    
    except Exception as e:
        return {"error": str(e)}

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

# DTS specific tools

# A tool for Claude to get a single corpus (because he can't work with the Resource template)
@mcp.tool()
def get_corpus_via_dts(corpus_name: str):
    """Get Information on a Corpus via the DTS API
    
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
    """Get Information on a Play via the DTS API"""
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

    This tool allows to retrieve structural information of a play. 
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
    """Get the Text of a Citable Unit
    
    Args:
        play_uri (str): Identifier/URI of the play, e.g. `https://staging.dracor.org/id/ger000088`
        ref (str): Fragment identifier, e.g of the first scene of the second act `body/div[2]/div[1]`
    """
    try:
        response = requests.get(f"{DRACOR_API_BASE_URL}/dts/document?resource={play_uri}&ref={ref}&mediaType=text/plain")
        return {"text": response.text}
    except Exception as e:
        return {"error": str(e)}

### --------------
###   PROMPTS
### --------------