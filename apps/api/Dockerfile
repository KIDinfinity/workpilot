# syntax=docker/dockerfile:1

# ---- builder：装依赖 + 编译字节码，产物只有 /app/.venv 与源码 ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# 1) 只用锁文件装第三方依赖：源码改动不会使这一层失效
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=apps/api/uv.lock,target=uv.lock \
    --mount=type=bind,source=apps/api/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# 2) 再拷源码并安装项目本身（prompts/ 在仓库根，需要一起进镜像）
COPY apps/api/ /app/
COPY prompts/ /app/prompts/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime：与 builder 同为 Debian bookworm + /usr/local/bin/python3.12，
#      .venv 里的解释器软链才有效 ----
FROM python:3.12-slim-bookworm AS runtime
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
RUN mkdir -p /app/data && chown app:app /app/data
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PROMPTS_DIR=/app/prompts
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
