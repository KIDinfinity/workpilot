import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import {
  api,
  type Conversation,
  type FeedbackRating,
  type FeedbackReason,
} from "../api/client";
import { AnswerMarkdown } from "../components/AnswerMarkdown";
import { CitationPanel } from "../components/CitationPanel";
import { ConversationList } from "../components/ConversationList";
import { FeedbackBar } from "../components/FeedbackBar";
import { useStreamingAnswer } from "../hooks/useStreamingAnswer";
import { uuid } from "../lib/uuid";
import type { Citation } from "../types/ui";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  messageId?: string; // 服务端消息 id，只有 assistant 且已落库的消息才有
  refused?: boolean;
  error?: boolean;
};

/** 把 fetch / HTTP 异常翻译成用户能看懂的提示。 */
function friendlyError(err: string | null): string {
  if (!err) return "";
  if (/Failed to fetch|NetworkError|Load failed/i.test(err)) {
    return "无法连接后端 API，请确认服务已启动后重试。";
  }
  const m = err.match(/HTTP (\d{3})/);
  if (m) return `后端返回 ${m[1]}，请稍后重试。`;
  return err.replace(/^Error:\s*/, "");
}

/** 历史消息里的 citations_json 是字符串，读出来还原成引用数组。 */
function parseCitations(json: string | null | undefined): Citation[] {
  if (!json) return [];
  try {
    return JSON.parse(json) as Citation[];
  } catch {
    return [];
  }
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [activeMsgId, setActiveMsgId] = useState<string | null>(null);
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const lastQuestion = useRef("");
  const listRef = useRef<HTMLUListElement>(null);

  const { status, answer, citations, error, start, stop } = useStreamingAnswer();
  const busy = status === "retrieving" || status === "streaming";

  const push = (m: Omit<ChatMessage, "id">) => {
    const id = uuid();
    setMessages((prev) => [...prev, { id, ...m }]);
    return id;
  };

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await api.listConversations());
    } catch {
      /* 左栏加载失败不打断聊天，保持现状 */
    }
  }, []);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, answer, status]);

  async function run(question: string) {
    lastQuestion.current = question;
    const r = await start(
      question,
      conversationId ? { conversation_id: conversationId } : {},
    );
    if (!r) return; // 用户停止或出错：交给状态条展示，不产生消息
    const id = push({
      role: "assistant",
      content: r.answer,
      citations: r.citations,
      refused: r.refused,
      messageId: r.messageId ?? undefined,
    });
    setActiveMsgId(id);
    setActiveCite(null);
    if (r.conversationId) setConversationId(r.conversationId);
    void loadConversations();
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    push({ role: "user", content: question });
    void run(question);
  }

  function onNew() {
    setConversationId(null);
    setMessages([]);
    setActiveMsgId(null);
    setActiveCite(null);
    setInput("");
  }

  async function onSelect(id: string) {
    setConversationId(id);
    setActiveMsgId(null);
    setActiveCite(null);
    try {
      const msgs = await api.listMessages(id);
      setMessages(
        msgs.map((m) => ({
          id: m.id ?? uuid(),
          role: m.role === "user" ? "user" : "assistant",
          content: m.content,
          citations: parseCitations(m.citations_json),
          messageId: m.role === "assistant" ? m.id : undefined,
        })),
      );
    } catch {
      setMessages([]);
    }
  }

  async function handleFeedback(
    messageId: string,
    rating: FeedbackRating,
    reason: FeedbackReason | null,
    comment: string,
  ) {
    await api.sendFeedback(messageId, { rating, reason, comment });
  }

  const live = status === "retrieving" || status === "streaming";
  const streaming = status === "streaming";
  const selected = messages.find((m) => m.id === activeMsgId);
  const shownCitations = live ? citations : (selected?.citations ?? []);

  function onCite(msgId: string | null, n: number) {
    if (msgId) setActiveMsgId(msgId);
    setActiveCite(n);
  }

  return (
    <div className="grid h-full grid-cols-[240px_minmax(0,1fr)_320px] gap-3 p-4">
      <ConversationList
        conversations={conversations}
        activeId={conversationId}
        onNew={onNew}
        onSelect={onSelect}
      />

      <section className="flex min-h-0 flex-col">
        <ul ref={listRef} className="flex-1 overflow-y-auto pr-1">
          {messages.length === 0 && !busy && (
            <li className="mt-8 text-center text-gray-400">
              输入问题，向知识库提问（答案带引用）。
            </li>
          )}
          {messages.map((m) => (
            <li
              key={m.id}
              className={`mb-2 flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded px-3 py-2 ${
                  m.error
                    ? "border border-red-200 bg-red-50 text-red-700"
                    : m.role === "user"
                      ? "whitespace-pre-wrap bg-blue-600 text-white"
                      : m.refused
                        ? "border border-amber-300 bg-amber-50 text-amber-900"
                        : "border border-gray-200 bg-gray-50 text-gray-800"
                }`}
              >
                {m.role === "assistant" && !m.error ? (
                  <>
                    {m.refused && (
                      <p className="mb-1 text-xs font-medium text-amber-700">
                        知识库中没有找到可靠依据
                      </p>
                    )}
                    <AnswerMarkdown text={m.content} onCite={(n) => onCite(m.id, n)} />
                    {m.messageId && (
                      <FeedbackBar
                        messageId={m.messageId}
                        onSubmit={(rating, reason, comment) =>
                          handleFeedback(m.messageId as string, rating, reason, comment)
                        }
                      />
                    )}
                  </>
                ) : (
                  m.content
                )}
              </div>
            </li>
          ))}
          {status === "retrieving" && (
            <li className="mb-2 text-sm text-gray-400">
              <span className="mr-1 inline-block animate-pulse">●</span>正在检索知识库…
            </li>
          )}
          {streaming && (
            <li className="mb-2 flex justify-start">
              <div className="max-w-[85%] rounded border border-gray-200 bg-gray-50 px-3 py-2 text-gray-800">
                <AnswerMarkdown text={answer} onCite={(n) => onCite(null, n)} />
                <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-gray-500 align-text-bottom" />
              </div>
            </li>
          )}
          {status === "done" && answer && (
            <li className="mb-2 text-xs text-gray-400">已完成</li>
          )}
        </ul>

        {status === "error" && (
          <div className="mb-2 flex items-center justify-between gap-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            <span>{friendlyError(error)}</span>
            <button
              type="button"
              onClick={() => void run(lastQuestion.current)}
              className="rounded border border-red-300 px-2 py-1 text-xs hover:bg-red-100"
            >
              重试
            </button>
          </div>
        )}

        {status === "idle" && answer && (
          <p className="mb-1 text-xs text-gray-400">已停止生成</p>
        )}

        <form onSubmit={onSubmit} className="mt-1 flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="输入问题（Enter 发送，Shift+Enter 换行）"
            rows={2}
            className="flex-1 resize-none rounded border border-gray-300 p-2"
          />
          {busy ? (
            <button
              type="button"
              onClick={stop}
              className="rounded bg-gray-700 px-4 text-white hover:bg-gray-800"
            >
              停止
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="rounded bg-blue-600 px-4 text-white disabled:opacity-50"
            >
              发送
            </button>
          )}
        </form>
      </section>

      <CitationPanel
        citations={shownCitations}
        active={activeCite}
        answer={live ? answer : (selected?.content ?? "")}
      />
    </div>
  );
}
