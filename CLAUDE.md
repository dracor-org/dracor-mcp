# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [FastMCP](https://gofastmcp.com) server (pinned to `fastmcp == 4.1.6`) exposing the DraCor (Drama Corpora Project) API v1 to LLMs. The entire server lives in a single file, `dracor_mcp.py`. There is no unit test suite or linter config; CI (`.github/workflows/test.yml`) builds the image, runs `test/smoke.py` against it, and builds for arm64.

## Commands

```sh
uv sync                                                        # set up .venv from uv.lock (Python from .python-version)
fastmcp dev inspector dracor_mcp.py                            # MCP Inspector for interactive testing of tools
python dracor_mcp.py                                           # run directly (uses DRACOR_MCP_TRANSPORT)
docker compose -f compose.dev.yml up                           # always rebuilds local dracor/mcp:dev, serves :8000/mcp
docker compose -f compose.sse.dev.yml up                       # same, with SSE transport on :8000/sse
docker compose up                                              # run published image dracor/mcp:<version>
python test/smoke.py [URL]                                     # check handshake + registered tools of a running server
```

The Docker image installs dependencies from `uv.lock` (`uv sync --frozen`), so run `uv lock` after changing dependencies in `pyproject.toml`.

## Configuration (environment variables)

- `DRACOR_API_BASE_URL` — DraCor API base, default `https://staging.dracor.org/api/v1`. Also used in the server name.
- `DRACOR_MCP_TRANSPORT` — `streamable-http` (default, path `/mcp`), `sse` (path `/sse`), or `stdio`. Only honored in the `if __name__ == "__main__"` block; `fastmcp run`/`fastmcp dev inspector` ignore it.
- `DRACOR_MCP_HTTP_HOST` / `DRACOR_MCP_HTTP_PORT` — address and port for the HTTP transports, default `0.0.0.0` / `8000`. Only honored in the `__main__` block, like `DRACOR_MCP_TRANSPORT`. Not `DRACOR_MCP_PORT`: Kubernetes sets `<SERVICE>_PORT=tcp://…` for a service named `dracor-mcp`. Read numeric settings with `env_number()`, which falls back to the default on empty or invalid (≤ 0, non-numeric) values and logs a warning.
- `DRACOR_MCP_ENABLE_ADMIN_TOOLS` — set to `true` to enable the write/admin tools (tagged `admin`, disabled with `mcp.disable(tags={"admin"})` otherwise). Must stay off on public deployments.
- `DRACOR_EXISTDB_ADMIN` / `DRACOR_EXISTDB_PWD` — HTTP Basic credentials for the write/admin tools against a local DraCor eXist-DB instance.
- `DRACOR_MCP_ALLOWED_HOSTS` / `DRACOR_MCP_ALLOWED_ORIGINS` — comma separated host names / origins accepted in the `Host` / `Origin` headers (DNS rebinding protection, `host_origin_protection=True`). localhost is always accepted; any other host gets HTTP 421, so deployments behind a proxy must set the host name.
- `DRACOR_HTTP_TIMEOUT` — timeout in seconds for outgoing requests, default 60.

## Architecture of `dracor_mcp.py`

- **Request helpers**: `api_request(endpoint, params)` (simple GET + JSON) and `api_get(corpusname, playname, method, parse_json)` which builds `/corpora/{corpus}/plays/{play}/{method}`-style URLs. Some tools call `requests` directly instead. (A TODO notes these should move to PyDraCor-Core.)
- **No resources**: the server exposes tools only (resources were removed, models don't use them).
- **Tools**, grouped by section comments: regular API endpoints; `*_helper` tools that post-process API data (paging, filtering by author/title/year, minimal play lists) to keep responses within LLM context limits; DTS (Distributed Text Services) endpoints; `get_corpus_registry` (the DraCor Registry's `corpora.json`); documentation tools that fetch and parse external sources (the DraCor ODD via `lxml`, research.md); and admin tools (`add_corpus`, `add_play_to_corpus`, `remove_*`, `load_corpus_from_repository`) that POST/PUT/DELETE with Basic auth.
- **Caching**: `cached(key, load)` keeps documents from GitHub (ODD, registry, research list, API README) for `DRACOR_CACHE_SECONDS` (1 h). Each key needs a lock in `_cache_locks`. Only one call loads at a time; others use the expired copy if there is one. A failed load is retried after `DRACOR_CACHE_RETRY_SECONDS` (1 min), serving the expired copy or the error meanwhile. API responses are not cached.
- **Server description**: `DRACOR_MCP_INSTRUCTIONS` is sent to clients as the MCP `instructions` (scope of DraCor, how to identify plays, cite sources). It is part of every session, so keep it short. The server version comes from `pyproject.toml`.
- **Conventions**: tools catch exceptions and return `{"error": str(e)}` rather than raising; successful results are usually wrapped in a dict keyed by the data type (e.g. `{"corpus": ...}`).
- **Building requests**: pass every value that comes from a tool argument through `path_segment()` when it goes into a URL path, and through `params=` when it goes into the query string, so arguments can't change the request (e.g. `../`, `?`, `&`). Send requests with `http_request(method, url, ...)`, not `requests` directly: it applies `DRACOR_HTTP_TIMEOUT`, turns a timeout into a message the model can act on, and raises on 4xx/5xx responses so the tool's `except` returns the status and URL. Pass `raise_for_status=False` only where a tool reports specific status codes itself (the admin tools). Paged tools call `check_paging()` before slicing. Use XPath variables (`root.xpath("//x[@id=$id]", id=...)`) instead of formatting values into XPath expressions.

## Docstrings are the product

Tool docstrings are what the LLM sees as the tool description (fastmcp moves the `Args:` section into the per-parameter descriptions of the input schema), and the project's evaluation ([arXiv:2508.13774](http://arxiv.org/abs/2508.13774), "Docstring Engineering") centers on them. When adding or editing tools, follow the existing docstring pattern: one-line summary, the source endpoint ("Data is retrieved from the endpoint ..."), pointers to alternative/paged tools when output may be large, and a Google-style `Args:` section with example identifiers (e.g. `ger`, `rus`). Keep the tool list in `README.md` in sync with the tools in the code.

## Releases

Version numbers are maintained by hand in `pyproject.toml`, `CITATION.cff` and the image tag in `compose.yml`; bump all of them together. The dev compose files intentionally build a local-only `dracor/mcp:dev` image (`pull_policy: build`) so they never shadow published tags. The base image is pinned to an exact tag (`python:3.13.x-slim-trixie`); Dependabot (`.github/dependabot.yml`, docker, monthly) opens PRs for new patch tags, so merge those before a release to pick up CPython and Debian security fixes. It ignores new Python minor versions; moving to one means changing `.python-version` and the `Dockerfile` together and checking that `uv.lock` still resolves. Publishing a GitHub release triggers `.github/workflows/publish_image_to_dockerhub.yml`, which builds multi-arch images and pushes `dracor/mcp` to DockerHub.
