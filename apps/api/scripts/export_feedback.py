"""导出 👎 反馈为 badcase 候选：cd apps/api && uv run python -m scripts.export_feedback"""

import json
from datetime import date
from pathlib import Path

from sqlmodel import Session, col, select

from app.db.models import Feedback, FeedbackRating, Message
from app.db.session import engine

OUT = (
    Path(__file__).resolve().parents[3]
    / "eval"
    / "badcases"
    / f"candidates-{date.today():%Y%m%d}.jsonl"
)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with Session(engine) as s, OUT.open("w", encoding="utf-8") as f:
        for fb in s.exec(select(Feedback).where(Feedback.rating == FeedbackRating.down)):
            ans = s.get(Message, fb.message_id)
            q = s.exec(
                select(Message)
                .where(
                    Message.conversation_id == ans.conversation_id,
                    Message.role == "user",
                    col(Message.created_at) <= ans.created_at,
                )
                .order_by(col(Message.created_at).desc())
            ).first()
            f.write(
                json.dumps(
                    {
                        "question": q.content if q else None,
                        "answer": ans.content,
                        "citations": json.loads(ans.citations_json or "[]"),
                        "reason": fb.reason,
                        "comment": fb.comment,
                        "message_id": ans.id,
                        "created_at": fb.created_at.isoformat(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            n += 1
    print(f"exported {n} candidates → {OUT}")


if __name__ == "__main__":
    main()
