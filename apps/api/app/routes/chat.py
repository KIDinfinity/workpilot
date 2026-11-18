import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.llm.gateway import LLMGateway
from app.llm.schemas import ChatRequest, ChatResult

router = APIRouter(prefix="/v1", tags=["llm"])
log = logging.getLogger(__name__)


def get_gateway(request: Request) -> LLMGateway:
    return request.app.state.gateway


@router.post("/chat", response_model=ChatResult)
async def chat(body: ChatRequest, gw: Annotated[LLMGateway, Depends(get_gateway)]) -> ChatResult:
    kw: dict[str, Any] = {"temperature": body.temperature}
    if body.max_tokens:
        kw["max_tokens"] = body.max_tokens
    return await gw.chat([m.model_dump() for m in body.messages], **kw)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, gw: Annotated[LLMGateway, Depends(get_gateway)]):
    async def gen():
        try:
            async for ev in gw.stream([m.model_dump() for m in body.messages]):
                if ev["type"] == "token":
                    yield sse("token", {"text": ev["text"]})
                else:
                    r = ev["result"]
                    yield sse(
                        "done",
                        r.model_dump(include={"request_id", "usage", "cost",
                                              "latency_ms", "ttft_ms", "usage_estimated"}),
                    )
        except Exception:
            log.exception("chat stream failed")
            # 不把内部异常细节返回给客户端
            yield sse("error", {"message": "LLM 调用失败，请稍后重试"})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
