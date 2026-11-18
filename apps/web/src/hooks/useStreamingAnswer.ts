import { useCallback, useRef, useState } from "react";
import { readSSE } from "../lib/sse";
import type { Citation, StreamStatus } from "../types/ui";

type State = {
  status: StreamStatus;
  answer: string;
  citations: Citation[];
  error: string | null;
};

const INIT: State = { status: "idle", answer: "", citations: [], error: null };

export type StreamResult = {
  answer: string;
  citations: Citation[];
  refused: boolean;
  done: Record<string, unknown>;
  conversationId?: string | null;
  messageId?: string | null;
};

type RawHit = {
  chunk_id?: string;
  doc_id?: string;
  title?: string;
  section?: string;
  snippet?: string;
  text?: string;
  score?: number;
};

/** 后端 retrieved 事件给的是 hits（1..n 顺序即 prompt 里的引用编号），这里补上 index。 */
function toCitations(hits: RawHit[]): Citation[] {
  return hits.map((h, i) => ({
    index: i + 1,
    doc_id: h.doc_id ?? h.chunk_id ?? "",
    title: h.title ?? "(未命名文档)",
    section: h.section,
    text: h.snippet ?? h.text ?? "",
    score: typeof h.score === "number" ? h.score : 0,
  }));
}

export function useStreamingAnswer() {
  const [state, setState] = useState<State>(INIT);
  const ctrlRef = useRef<AbortController | null>(null);

  const start = useCallback(
    async (question: string, extra: Record<string, unknown> = {}) => {
      ctrlRef.current?.abort(); // 新问题取消旧请求
      const ctrl = (ctrlRef.current = new AbortController());
      setState({ ...INIT, status: "retrieving" });
      let answer = "";
      let citations: Citation[] = [];
      try {
        const res = await fetch("/v1/kb/ask/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, ...extra }),
          signal: ctrl.signal,
        });
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
        for await (const { event, data } of readSSE(res.body)) {
          const p = JSON.parse(data) as Record<string, unknown>;
          if (event === "retrieved") {
            citations = toCitations((p.hits as RawHit[]) ?? []);
          }
          if (event === "token") answer += (p.text as string) ?? "";
          if (event === "error") {
            throw new Error((p.message as string) ?? "服务端错误");
          }
          const status: StreamStatus =
            event === "done" ? "done" : answer ? "streaming" : "retrieving";
          setState({ status, answer, citations, error: null });
          if (event === "done") {
            return {
              answer,
              citations,
              refused: !!p.refused,
              done: p,
              conversationId: (p.conversation_id as string | undefined) ?? null,
              messageId: (p.message_id as string | undefined) ?? null,
            } satisfies StreamResult;
          }
        }
        throw new Error("流意外结束（未收到 done）");
      } catch (e) {
        const aborted = ctrl.signal.aborted; // 用户点停止不算错误
        const error = aborted ? null : String(e);
        setState((s) => ({ ...s, status: aborted ? "idle" : "error", error }));
        return null;
      }
    },
    [],
  );

  const stop = useCallback(() => ctrlRef.current?.abort(), []);
  return { ...state, start, stop };
}
