FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Omit development dependencies
ENV UV_NO_DEV=1

# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Install the project into `/app`
WORKDIR /app

# Install the project's dependencies using the lockfile and settings
COPY uv.lock pyproject.toml ./
RUN uv sync --locked --no-install-project

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN uv sync --locked

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the FastAPI application by default
CMD ["uv", "run", "fastapi", "run"]
