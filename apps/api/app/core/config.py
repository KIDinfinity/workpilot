from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.llm_providers import PROVIDERS

# 本文件在 workpilot/apps/api/app/core/config.py
# parents[0]=core [1]=app [2]=api [3]=apps [4]=workpilot（仓库根，.env 所在）
# 容器内源码被拷到 /app/app（只有 3 层父目录），退到 /app；PROMPTS_DIR 等仍可被环境变量覆盖
_SRC = Path(__file__).resolve()
ROOT_DIR = _SRC.parents[4] if len(_SRC.parents) > 4 else _SRC.parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env 里有 EMBEDDING_/MINIO_ 等暂未使用的键，忽略而不是报错
    )

    app_env: Literal["dev", "test", "prod"] = "dev"  # 对应 APP_ENV（大小写不敏感）
    log_level: str = "INFO"
    log_json: bool = True  # LOG_JSON=0 切回纯文本日志（本地调试用）
    app_version: str = "0.0.1"

    # ===== 数据库（Day24 会话 / 消息 / 反馈）=====
    # 与 .env / .env.example 的 DATABASE_URL 保持一致（W6 SQLite，W19 改 Postgres）。
    # 相对 apps/api 运行目录；默认值仅在 .env 未配置时生效。
    database_url: str = "sqlite:///./data/app.db"

    # ===== LLM（供应商预设见 app/core/llm_providers.py）=====
    # 切换供应商只改 LLM_PROVIDER 一行；两个 key 分开存，切回来不用重填
    llm_provider: Literal["deepseek", "doubao", "ollama"] = "deepseek"
    deepseek_api_key: SecretStr = SecretStr("")
    doubao_api_key: SecretStr = SecretStr("")
    llm_model: str = ""  # 留空 = 用预设模型；填了则覆盖（如火山方舟的 ep-xxxxxxxx）
    llm_timeout_s: float = 30.0
    llm_max_attempts: int = 3

    # 版本化 prompt 目录（仓库根/prompts/*.vN.md）
    prompts_dir: Path = ROOT_DIR / "prompts"

    # ===== 成本计量（价格每百万 tokens，未配置则 cost=None，不猜）=====
    price_currency: str = "CNY"
    price_input_hit_per_m: float | None = None     # 每百万 tokens，缓存命中输入
    price_input_miss_per_m: float | None = None    # 每百万 tokens，缓存未命中输入
    price_output_per_m: float | None = None        # 每百万 tokens，输出
    llm_log_path: Path = ROOT_DIR / "data" / "logs" / "llm_calls.jsonl"

    # ===== 对象存储 MinIO（S3 兼容，ingest --upload-raw 用）=====
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: SecretStr = SecretStr("")

    # ===== Embedding（bge-m3，1024 维）=====
    embedding_base_url: str = "http://localhost:11434/v1"  # EMBEDDING_BASE_URL
    embedding_api_key: str = "ollama"                      # EMBEDDING_API_KEY（Ollama 忽略值）
    embedding_model: str = "bge-m3"                        # EMBEDDING_MODEL
    embed_dim: int = 1024
    embed_batch: int = 32

    # ===== 向量库 Qdrant =====
    qdrant_url: str = "http://localhost:6333"  # QDRANT_URL

    # ===== Chunking（W5 实验直接改参数换 collection 重建）=====
    chunk_size: int = 600
    chunk_overlap: int = 100
    workspace: str = "default"

    # ===== RAG 检索 / 带引用回答（Day17）=====
    top_k: int = 5
    retrieval_mode: Literal["dense", "hybrid"] = "dense"  # RETRIEVAL_MODE（ADR 0003）
    score_threshold: float | None = None  # 今天先不设，看完分数分布再定
    answer_prompt: str = "qa_answer.v1"

    @model_validator(mode="after")
    def _validate_runtime(self) -> "Settings":
        """fail fast：缺密钥 / prod 用本机 Ollama 时，进程启动即失败而非等首个请求报错。

        - test 环境用注入的假 Settings，跳过真实密钥与 prod 约束。
        - 密钥缺失不在此处打印密钥本身，只指明缺哪个字段。
        """
        if self.app_env == "test":
            return self
        if self.app_env == "prod":
            if self.embedding_api_key in ("", "ollama"):
                raise ValueError("APP_ENV=prod 需要真实的 EMBEDDING_API_KEY（SiliconFlow）")
            if ":11434" in self.embedding_base_url:
                raise ValueError("APP_ENV=prod 不能使用本机 Ollama 作为 embedding")
        if self.llm_provider != "ollama" and not self.llm_api_key.get_secret_value():
            raise ValueError(
                f"LLM_PROVIDER={self.llm_provider} 需要 {self.llm_provider.upper()}_API_KEY"
            )
        return self

    @property
    def llm_base_url(self) -> str:
        return PROVIDERS[self.llm_provider].base_url

    @property
    def llm_model_name(self) -> str:
        return self.llm_model or PROVIDERS[self.llm_provider].model

    @property
    def llm_api_key(self) -> SecretStr:
        own = getattr(self, f"{self.llm_provider}_api_key", None)
        if isinstance(own, SecretStr) and own.get_secret_value():
            return own
        return SecretStr(PROVIDERS[self.llm_provider].api_key)

    @property
    def llm_extra_body(self) -> dict:
        """供应商要求的额外请求体字段，如豆包关思考：{"thinking": {"type": "disabled"}}。"""
        return PROVIDERS[self.llm_provider].extra_body


@lru_cache
def get_settings() -> Settings:
    """进程内只解析一次 .env；测试中用 dependency_overrides 替换。"""
    return Settings()


# 模块级单例，供非 DI 场景（RAG ingest / embed / store）直接 import 使用
settings = get_settings()
