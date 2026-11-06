# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [FastMCP](https://gofastmcp.com) server (pinned to `fastmcp == 2.11.3`) exposing the DraCor (Drama Corpora Project) API v1 to LLMs. The entire server lives in a single file, `dracor_mcp.py`. There is no test suite, linter config, or CI beyond the Docker image publish workflow.

## Commands

```sh
uv venv && source .venv/bin/activate && uv pip install -e .   # set up
fastmcp dev dracor_mcp.py                                      # MCP Inspector for interactive testing of tools
python dracor_mcp.py                                           # run directly (uses DRACOR_MCP_TRANSPORT)
docker compose -f compose.dev.yml up                           # always rebuilds local dracor/mcp:dev, serves :8000/mcp
docker compose -f compose.sse.dev.yml up                       # same, with SSE transport on :8000/sse
docker compose up                                              # run published image dracor/mcp:<version>
```

## Configuration (environment variables)

- `DRACOR_API_BASE_URL` — DraCor API base, default `https://staging.dracor.org/api/v1`. Also used to derive the RelaxNG schema URL (`<host>/schema.rng`) and the server name.
- `DRACOR_MCP_TRANSPORT` — `streamable-http` (default, path `/mcp`), `sse` (path `/sse`), or `stdio`. Only honored in the `if __name__ == "__main__"` block; `fastmcp run`/`fastmcp dev` ignore it.
- `DRACOR_EXISTDB_ADMIN` / `DRACOR_EXISTDB_PWD` — HTTP Basic credentials for the write/admin tools against a local DraCor eXist-DB instance.

## Architecture of `dracor_mcp.py`

- **Request helpers**: `api_request(endpoint, params)` (simple GET + JSON) and `api_get(corpusname, playname, method, parse_json)` which builds `/corpora/{corpus}/plays/{play}/{method}`-style URLs. Some tools call `requests` directly instead. (A TODO notes these should move to PyDraCor-Core.)
- **Resources**: `corpora://` (via DTS collection) and `registry://` (DraCor registry JSON from GitHub). A templated `corpora://{corpus_name}` resource is commented out because Claude Desktop doesn't support resource templates.
- **Tools**, grouped by section comments: regular API endpoints; `*_helper` tools that post-process API data (paging, filtering by author/title/year, minimal play lists) to keep responses within LLM context limits; DTS (Distributed Text Services) endpoints; documentation tools that fetch and parse external sources at call time (API ontology TTL via `rdflib`, the DraCor ODD via `lxml`, OpenAPI spec, research.md, RelaxNG validation); and admin tools (`add_corpus`, `add_play_to_corpus`, `remove_*`, `load_corpus_from_repository`) that POST/PUT/DELETE with Basic auth.
- **Conventions**: tools catch exceptions and return `{"error": str(e)}` rather than raising; successful results are usually wrapped in a dict keyed by the data type (e.g. `{"corpus": ...}`).

## Docstrings are the product

Tool docstrings are what the LLM sees as the tool description, and the project's evaluation ([arXiv:2508.13774](http://arxiv.org/abs/2508.13774), "Docstring Engineering") centers on them. When adding or editing tools, follow the existing docstring pattern: one-line summary, the source endpoint ("Data is retrieved from the endpoint ..."), pointers to alternative/paged tools when output may be large, and a Google-style `Args:` section with example identifiers (e.g. `ger`, `rus`). Keep the tool list in `README.md` in sync with the tools in the code.

## Releases

Version numbers are maintained by hand in `pyproject.toml`, `CITATION.cff` and the image tag in `compose.yml`; bump all of them together. The dev compose files intentionally build a local-only `dracor/mcp:dev` image (`pull_policy: build`) so they never shadow published tags. Publishing a GitHub release triggers `.github/workflows/publish_image_to_dockerhub.yml`, which builds multi-arch images and pushes `dracor/mcp` to DockerHub.
