import { useState } from "react";
import type { FeedbackRating, FeedbackReason } from "../api/client";

const REASONS: { value: FeedbackReason; label: string }[] = [
  { value: "wrong", label: "答案事实错误" },
  { value: "no_citation", label: "没有引用 / 引用对不上" },
  { value: "irrelevant", label: "答非所问 / 检索跑偏" },
  { value: "incomplete", label: "不完整" },
  { value: "other", label: "其他" },
];

export function FeedbackBar({
  messageId,
  onSubmit,
}: {
  messageId: string | null;
  onSubmit: (rating: FeedbackRating, reason: FeedbackReason | null, comment: string) => Promise<void>;
}) {
  const [done, setDone] = useState<FeedbackRating | null>(null);
  const [showDown, setShowDown] = useState(false);
  const [reason, setReason] = useState<FeedbackReason>("wrong");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!messageId) return null;

  const send = async (rating: FeedbackRating, r: FeedbackReason | null, c: string) => {
    if (done) return;
    setSubmitting(true);
    try {
      await onSubmit(rating, r, c);
      setDone(rating);
      setShowDown(false);
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="mt-1 text-xs text-gray-400">
        {done === "up" ? "👍 已反馈：有帮助" : "👎 已反馈，谢谢你的意见"}
      </div>
    );
  }

  return (
    <div className="mt-1 border-t border-gray-100 pt-1">
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">这条回答有帮助吗？</span>
        <button
          type="button"
          disabled={submitting}
          onClick={() => void send("up", null, "")}
          className="rounded border border-gray-200 px-2 py-0.5 text-sm hover:bg-gray-100 disabled:opacity-50"
          aria-label="有帮助"
        >
          👍
        </button>
        <button
          type="button"
          disabled={submitting}
          onClick={() => setShowDown((v) => !v)}
          className="rounded border border-gray-200 px-2 py-0.5 text-sm hover:bg-gray-100 disabled:opacity-50"
          aria-label="没有帮助"
        >
          👎
        </button>
      </div>

      {showDown && (
        <div className="mt-2 space-y-2 rounded border border-gray-200 bg-white p-2">
          <label className="block text-xs text-gray-600">
            原因
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value as FeedbackReason)}
              className="mt-1 block w-full rounded border border-gray-300 p-1 text-sm"
            >
              {REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs text-gray-600">
            备注（可选）
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={2}
              className="mt-1 block w-full resize-none rounded border border-gray-300 p-1 text-sm"
              placeholder="补充说明…"
            />
          </label>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowDown(false)}
              className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100"
            >
              取消
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={() => void send("down", reason, comment.trim())}
              className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
            >
              提交
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
