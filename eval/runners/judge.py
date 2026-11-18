from typing import Literal

from pydantic import BaseModel, Field

from app.llm.gateway import LLMGateway
from app.llm.prompts import load_prompt
from app.llm.structured import generate_structured


class JudgeResult(BaseModel):
    correctness: Literal[0, 1, 2]
    faithfulness: Literal["yes", "partial", "no"]
    citation_correct: bool
    reason: str = Field(max_length=60)


async def judge_one(
    question: str,
    expected: str,
    context: str,
    answer: str,
    gw: LLMGateway,
) -> tuple[JudgeResult, float | None]:
    prompt = load_prompt("judge_answer.v1")
    message = prompt.render(
        question=question,
        expected_answer=expected,
        context=context or "（无检索结果）",
        answer=answer,
    )
    result, response = await generate_structured(
        JudgeResult,
        [{"role": "user", "content": message}],
        gw=gw,
        temperature=0,
    )
    return result, response.cost


def agreement(
    judged: dict[str, JudgeResult],
    gold: list[dict],
) -> dict[str, float | int]:
    gold_by_id = {item["id"]: item for item in gold}
    ids = [item_id for item_id in judged if item_id in gold_by_id]
    denominator = len(ids) or 1
    return {
        "n": len(ids),
        "correctness": sum(
            judged[item_id].correctness == gold_by_id[item_id]["correctness"] for item_id in ids
        )
        / denominator,
        "faithfulness": sum(
            judged[item_id].faithfulness == gold_by_id[item_id]["faithfulness"] for item_id in ids
        )
        / denominator,
        "citation": sum(
            judged[item_id].citation_correct == gold_by_id[item_id]["citation_correct"]
            for item_id in ids
        )
        / denominator,
    }
