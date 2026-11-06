FROM python:3.13.18-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

WORKDIR /home/mcp

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install the locked dependencies only; the server is a single module.
# OpenShift/OKD runs containers with an arbitrary UID that belongs to group 0,
# so the files belong to group 0 with the same permissions as the owner (g=u).
# Done in the same layer as the install so the venv is not copied twice.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project \
    && chgrp -R 0 /home/mcp \
    && chmod -R g=u /home/mcp

COPY --chown=10001:0 --chmod=664 dracor_mcp.py ./

# The server writes nothing at runtime; HOME points to /tmp in case a library
# wants a home directory. Works with a read-only root filesystem.
ENV HOME=/tmp \
    PYTHONUNBUFFERED=1

# Numeric user, so that Kubernetes can verify runAsNonRoot. Any other UID in
# group 0 (as assigned by OKD) works as well.
USER 10001:0

EXPOSE 8000

CMD [".venv/bin/python", "dracor_mcp.py"]
