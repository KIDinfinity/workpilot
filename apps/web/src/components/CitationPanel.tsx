import { useEffect } from "react";
import type { Citation } from "../types/ui";

export function CitationPanel({
  citations,
  active,
  answer = "",
}: {
  citations: Citation[];
  active: number | null;
  answer?: string;
}) {
  useEffect(() => {
    if (active == null) return;
    document
      .getElementById(`cite-card-${active}`)
      ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [active]);

  const countOf = (n: number) =>
    answer ? (answer.match(new RegExp(`\\[${n}\\]`, "g")) ?? []).length : 0;

  return (
    <aside className="flex h-full flex-col overflow-hidden rounded border border-gray-200 bg-gray-50">
      <header className="border-b border-gray-200 px-3 py-2 text-sm font-medium text-gray-700">
        引用来源 {citations.length > 0 && `(${citations.length})`}
      </header>
      <div className="flex-1 space-y-2 overflow-y-auto p-2">
        {citations.length === 0 && (
          <p className="p-2 text-xs text-gray-400">提问后在这里显示检索到的原文片段。</p>
        )}
        {citations.map((c) => {
          const isActive = active === c.index;
          return (
            <article
              key={`${c.index}-${c.doc_id}`}
              id={`cite-card-${c.index}`}
              className={`rounded border bg-white p-2 text-xs transition ${
                isActive ? "ring-2 ring-blue-500" : "border-gray-200"
              }`}
            >
              <div className="flex items-start gap-1">
                <span className="rounded bg-blue-100 px-1 text-[10px] text-blue-700">
                  [{c.index}]
                </span>
                <h3 className="flex-1 font-medium text-gray-800">{c.title}</h3>
                <span className="text-gray-400">{c.score.toFixed(2)}</span>
              </div>
              {c.section && (
                <p className="mt-1 line-clamp-2 text-[11px] text-gray-500">{c.section}</p>
              )}
              <p className="mt-1 line-clamp-6 whitespace-pre-wrap text-gray-600">{c.text}</p>
              {countOf(c.index) > 0 && (
                <p className="mt-1 text-[10px] text-gray-400">
                  在答案中被引用 {countOf(c.index)} 次
                </p>
              )}
            </article>
          );
        })}
      </div>
    </aside>
  );
}
