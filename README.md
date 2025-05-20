# DraCor MCP Server

A Model Context Protocol (MCP) server for interacting with the Drama Corpora Project (DraCor). This MCP server enables you to seamlessly analyze dramatic texts and their character networks through Claude or other LLMs.

## Overview

This project implements an MCP server using the official Model Context Protocol Python SDK that provides access to the DraCor API v1. It allows Claude and other LLMs to interact with dramatic text corpora, analyze character networks, retrieve play information, and generate insights about dramatic works across different languages and periods.

## Features

- Access to DraCor API v1 through a unified interface
- No authentication required (DraCor API is publicly accessible)
- Support for operations:
  - Corpora and play information retrieval
  - Metrics and statistics for plays
  - Character information and spoken text
  - Character network analysis
  - Stage Directions
  - Full text retrieval in plain text and TEI XML format
  - Granular Access to segments of a play via DTS (Distributed Text Services) API
  - Access to DraCor's documentation (ODD, OpenAPI, API Features Ontology)

## Setup

### Prerequisites

- Python 3.10 or higher
- UV package manager (recommended) or pip

### Installation with UV

1. Clone the repository

```
git clone git@github.com:dracor-org/dracor-mcp.git
```

2. Install UV:

```
pip install uv
```

3. Create a virtual environment and install dependencies:

```
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

4. Add the MCP server in Claude Desktop:

Add the following to your Claude configuration file:

```json
{
  "mcpServers": {
    "DraCor": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with",
        "requests",
        "--with",
        "pydantic",
        "--with",
        "python-multipart",
        "--with",
        "rdflib",
        "--with",
        "lxml",
        "mcp",
        "run",
        "/path/to/dracor-mcp/dracor_mcp.py"
      ],
      "env": {
        "DRACOR_API_BASE_URL": "https://staging.dracor.org/api/v1"
      }
    }
  }
}
```

Replace `/path/to/dracor-mcp/` with the actual absolute path to your dracor-mcp directory. This configuration uses `uv run` to execute the MCP server with the necessary dependencies without requiring a prior installation.

If you want to use a different server, e.g. the staging server, change it in the environment variable `DRACOR_API_BASE_URL` in the configuration file:

```json
"env": {
  "DRACOR_API_BASE_URL": "https://staging.dracor.org/api/v1" 
  }
```

If running DraCor locally you can set the admin user of the eXist-DB and the password by adding the environment variables `DRACOR_EXISTDB_ADMIN` and `DRACOR_EXISTDB_PWD`:

```json
"env": {
  "DRACOR_API_BASE_URL": "http://localhost:8088/api/v1",
  "DRACOR_EXISTDB_ADMIN": "admin",
  "DRACOR_EXISTDB_PWD": ""
  }
```

### Development Mode

For testing and development:

```
mcp dev dracor_mcp.py
```

This will launch the MCP Inspector where you can test your tools and resources interactively.

## Usage

Once installed in Claude Desktop, you can interact with the DraCor API through Claude. Here are some examples:

### Basic Queries

1. Ask Claude to explain the DraCor API

```
What can I do with the DraCor API?
```

2. Ask Claude to list available corpora:

```
Can you list all available drama corpora in DraCor?
```

3. Get information about a specific play:

```
Tell me about Goethe's Faust in the German corpus
```

4. Analyze character networks:

```
Analyze the character network in Hamlet from the Shakespeare corpus
```

5. Learn about DraCor TEI encoding:

```
How is the translated English title of a play encoded in the TEI?
```

6. Have data structures returned by the DraCor API explained:

```
What is the normalized year?
```

7. Manage a local DraCor instance running as Docker container:

``` 
Add a corpus with the name "mycor" to my local DraCor instance and add the play I provide you with.
```

### Advanced Queries

TBD

## Tools (v1 API)

The DraCor FastMCP server provides the following tools:

### API Information
- `get_api_info` - Get general information about the DraCor API
- `get_api_feature_list` - Get a list of supported API features
- `get_api_feature` - Get description of a specific API feature
- `get_openapi_specification` - Get the complete OpenAPI Specification

### Corpora
- `get_corpora` - List all available drama corpora
- `get_corpus` - Get information on a single corpus
- `get_corpus_metadata` - Get extended metadata of all plays in a corpus
- `get_corpus_metadata_paged_helper` - Get metadata on plays in a corpus in batches
- `get_corpus_contents_paged_helper` - Get corpus contents in batches

### Play Discovery and Filtering
- `get_minimal_data_of_plays_of_corpus_helper` - Get minimal play data (title, author, year)
- `get_playnames_in_corpus_helper` - Get identifiers of plays in a corpus
- `get_plays_in_corpus_by_author_helper` - Filter plays by author in a corpus
- `get_plays_in_corpus_by_title_helper` - Filter plays by title in a corpus
- `get_plays_in_corpus_by_year_normalized` - Get plays in a corpus by year range

### Play Information
- `get_play_metadata` - Get metadata and network metrics of a play
- `get_play_metrics` - Get network metrics of a play
- `get_play_tei` - Get TEI-XML of a play
- `get_play_plaintext` - Get plaintext of a play
- `get_links_to_playdata_helper` - Get download and external tool links for a play

### Characters and Relationships
- `get_play_characters` - Get characters of a play
- `get_play_network` - Get the co-presence network of a play
- `get_play_character_relations` - Get character relations in a play
- `get_plays_with_characters_by_wikidata_id` - Find plays with a character by Wikidata ID

### Text Content
- `get_spoken_text` - Get spoken text of a play (excluding stage directions)
- `get_spoken_text_by_characters` - Get spoken text of each character in a play
- `get_spoken_text_of_single_character` - Get spoken text of a specific character
- `get_stage_directions` - Get text of all stage directions in a play
- `get_stage_directions_with_speakers` - Get stage directions including speakers

### DTS (Distributed Text Services) API
- `dts_entrypoint` - Get DTS API entry point
- `get_corpus_via_dts` - Get corpus information through DTS API
- `get_play_via_dts` - Get play information through DTS API
- `get_citable_units_via_dts` - Get structural information of a play via DTS
- `get_plaintext_of_citable_unit_via_dts` - Get text of a specific section of a play

### External Data
- `get_author_info_from_wikidata` - Get information about an author from Wikidata
- `get_wikidata_mixnmatch` - Get Wikidata Mix'n'Match data for DraCor
- `get_dracor_based_research` - Get research based on DraCor

### Documentation
- `get_table_of_contents_from_odd` - Get table of contents of the DraCor ODD
- `get_odd_section` - Get a specific section of the ODD documentation
- `get_tei_element_documentation_from_odd` - Get documentation for a TEI element
- `get_schematron_rule_to_check_api_feature` - Get Schematron rule for API feature

### Database Management Tools
- `add_corpus` - Add a new corpus to a (local) DraCor instance
- `load_corpus_from_repository` - Load plays from a GitHub repository into a (local) DraCor instance
- `add_play_to_corpus` - Add a TEI-file of a play to a corpus in a (local) DraCor instance
- `remove_play_from_corpus` - Remove a play from a corpus in a (local) DraCor instance
- `remove_corpus` - Remove a corpus from a (local) DraCor instance

## How It Works

This project uses the official Model Context Protocol Python SDK to build an MCP server that exposes resources and tools that Claude can use to interact with the DraCor API.

When you ask Claude a question about dramatic texts, it can:

1. Access resources like corpora, plays, characters, and networks
2. Use tools to search, compare, and analyze plays
3. Provide insights and visualizations based on the data

The DraCor API is publicly accessible, so no authentication is required.

## License

MIT

## Acknowledgements

We'd like to thank [Stijn Meijers](https://github.com/stijn-meijers) of [wolk](https://www.wolk.work) for the inspiration and initial work on this MCP server. His contributions provided the foundation for this interface, enabling effective access to the DraCor API and its drama corpora resources via LLMs.

In the context of [CLS INFRA](https://clsinfra.io), the project has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement [No. 101004984](https://cordis.europa.eu/project/id/101004984).

We acknowledge the [OSCARS](https://oscars-project.eu/) project, which has received funding from the European Commission’s Horizon Europe Research and Innovation programme under grant agreement [No. 101129751](https://cordis.europa.eu/project/id/101129751).
