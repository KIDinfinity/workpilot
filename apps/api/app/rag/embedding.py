from openai import AsyncOpenAI

from app.core.config import settings


class Embedder:
    def __init__(self) -> None:
        # Ollama 忽略 key，但 OpenAI SDK 必填；SiliconFlow 时换成真实 key
        self.client = AsyncOpenAI(
            base_url=settings.embedding_base_url, api_key=settings.embedding_api_key
        )
        self.model, self.batch, self.dim = (
            settings.embedding_model,
            settings.embed_batch,
            settings.embed_dim,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            resp = await self.client.embeddings.create(
                model=self.model, input=texts[i : i + self.batch]
            )
            out.extend(d.embedding for d in resp.data)
        if any(len(v) != self.dim for v in out):
            raise ValueError(f"embedding 维度不是 {self.dim}，检查模型是否为 bge-m3")
        return out


embedder = Embedder()
