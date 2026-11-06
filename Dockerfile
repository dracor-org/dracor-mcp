FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

WORKDIR /home/mcp

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install the locked dependencies only; the server is a single module
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY dracor_mcp.py ./

RUN useradd --system --no-create-home mcp
USER mcp

EXPOSE 8000

CMD [".venv/bin/python", "dracor_mcp.py"]
